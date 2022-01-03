"""
站外iherb.sg_https://sg.iherb.com
(抓取频次 per 6 weeks(TBD))
爬取红框所示5大主类:
    - Bath
    - Beauty
    - Grocery
    - Healthy Home
    - Baby

Detail request:
    https://j77o203gb7.larksuite.com/docs/docusSJ5XJvBpVY8PPwWXq1xXNg#
"""


from numpy import product
import requests, re, json
# import system time module for specific delay to avoid being blocked
# import time
# main data crawl parser class for HTML content
from bs4 import BeautifulSoup
# database connection
from db_connection import get_connection

# append last path-variable for the category
# request parameters: sr=2 for best sellers, noi=48 for page size, p=1 for page number, 
API_LISTING_PAGE = 'https://sg.iherb.com/c/<path>?noi=48&sr=2&p='
# request with product id
API_RATINGS = 'https://sg.iherb.com/ugc/api/product/<id>/review/summary'


def extract_price(price: str) -> float:
    if g := re.search(r'\d+\.?\d+', price):
        return float(g.group(0))

    return 0


def get_price(soup: BeautifulSoup, name='default') -> dict:
    price_before = 0
    p_div = soup.find('div', {'id': 'price'})
    if p_div is None:
        # sold out
        return None
    price_after = extract_price(soup.find('div', {'id': 'price'}).contents[0])
    if special := soup.find('section', {'id': 'super-special-price'}):
       price_before, price_after = price_after, extract_price(special.findChildren('b')[0].contents[0]) 
    return {
        'name': name,
        'before': price_before,
        'after': price_after
    }


def process_model_div(div) -> dict:
    url = div['data-url']
    res = requests.get(url)
    html = "".join(line.strip() for line in res.text.split("\n"))
    soup = BeautifulSoup(html, 'html.parser')
    return get_price(soup, name=div['data-val'])


def extract_models(soup: BeautifulSoup):
    div = soup.find('div', class_='attribute-group-package-quantity attribute-tile-group')

    if div is None:
        # only default model present
        return [get_price(soup)]

    # there are multiple models for a product
    return [process_model_div(d) for d in div.findChildren('div', recursive=False)]


def process_detail(product_id: int, soup: BeautifulSoup, conn, cur):
    cur.execute('delete from iherb_model where product_id = %s', (product_id, ))

    models = extract_models(soup)
    for m in [i for i in models if i is not None]:
        cur.execute(
            """
                insert into iherb_model (product_id, model_name, price_before, price_after)
                values (%s, %s, %s, %s)
            """, (product_id, m['name'], m['before'], m['after'])
        )

    conn.commit()


def get_product_rank(soup: BeautifulSoup) -> str:
    if rank := soup.find('div', class_='best-selling-rank'):
        return '\n'.join([
            d.findChildren('strong', class_='rank')[0].contents[0].replace('\n', '') + ' ' + \
            d.findChildren('a')[0].findChildren('strong')[0].contents[0].replace('\n', '') \
            for d in rank.findChildren('div', recursive=False)
        ])

    return 'NA'


def get_breadcrumb(soup: BeautifulSoup):
    brand, path = 'NA', 'NA'
    if bread := soup.find('div', {'id': 'breadCrumbs'}):
        refs = [
            a.contents[0]
            for a in bread.findChildren('a', recursive=False)
        ]
        brand, path = refs[1], ' > '.join(refs[3:])

    return brand, path


def get_image(soup: BeautifulSoup) -> str:
    if image := soup.find('img', {'id': 'iherb-product-image'}):
        return image['src']
    return 'NA'


def get_name(soup: BeautifulSoup) -> str:
    return soup.find('div', {'id': 'name'}).contents[0]


def get_overview(soup: BeautifulSoup) -> str:
    return soup.find('div', class_='container product-overview').decode_contents()


def get_reviews_ratings(product_id: int, soup: BeautifulSoup):
    reviews = soup.find('a', class_='rating-count').findChildren('span')[0].contents[0]
        
    url = API_RATINGS.replace('<id>', str(product_id))
    res = requests.get(url)
    data = json.loads(res.text)

    ratings = data['rating']['averageRating']
    
    return int(reviews), ratings


def process_item(product_id: int, url: str, category: str, soup: BeautifulSoup, conn, cur):
    rank = get_product_rank(soup)
    brand, path = get_breadcrumb(soup)
    image = get_image(soup)
    name = get_name(soup)
    overview = get_overview(soup)
    reviews, ratings = get_reviews_ratings(product_id, soup)


    cur.execute("select 1 from iherb_product where product_id = %s", (product_id, ))
    p = cur.fetchone()

    if p is None:
        # new product
        cur.execute(
            """
                insert into iherb_product (product_id, product_category, product_link, product_path, product_image, product_brand, product_name, product_rank, product_overview, reviews, ratings, last_update)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, current_timestamp)
            """, (product_id, category, url, path, image, brand, name, rank, overview, reviews, ratings)
        )
    else:
        # updating existing
        cur.execute(
            """
                update iherb_product
                set product_link = %s,
                    product_path = %s,
                    product_image = %s,
                    product_brand = %s,
                    product_name = %s,
                    product_rank = %s,
                    product_overview = %s,
                    reviews = %s,
                    ratings = %s,
                    last_update = current_timestamp
                where product_id = %s
            """, (url, path, image, brand, name, rank, overview, reviews, ratings, product_id)
        )

    conn.commit()


def pull_item(item: dict, conn, cur):
    print("Pulling", item['link'], item['title'])
    url = item['link']
    res = requests.get(url)
    html = "".join(line.strip() for line in res.text.split("\n"))
    soup = BeautifulSoup(html, 'html.parser')

    product_id = int(item['product-id'])

    # insert into iherb_product table
    process_item(product_id, url, item['category'], soup, conn, cur)

    # insert into iherb_model table
    process_detail(product_id, soup, conn, cur)


def pull_list(page: int, category: str, cat_name: str, conn, cur) -> list:
    url = API_LISTING_PAGE.replace('<path>', category) + str(page)
    print("Pulling list from", url)
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    product_links = soup.find_all('a', class_='absolute-link product-link')
    return [
        {
            'product-id': p['data-ga-product-id'],
            'part-number': p['data-part-number'],
            'link': p['href'],
            'title': p['title'],
            'category': cat_name
        }
        for p in product_links
    ]


def main():
    # main entry method for crawling i-herb data from web
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("set search_path = data")
    
    # categories to be pulled from the iherb website
    categories = [
        ('bath-personal-care', 'Bath'),
        ('beauty', 'Beauty'),
        ('grocery', 'Grocery'),
        ('healthy-home', 'Healthy Home'),
        ('baby-kids', 'Baby')
    ]

    for c in categories:
        # pull pages from 1 to 5 for each category of best sellers
        for p in range(1, 6):
            items = pull_list(p, c[0], c[1], conn, cur)
            print("Total number of items pulled", len(items))
            for i in items:
                pull_item(i, conn, cur)


if __name__ == "__main__":
    main()
