from numpy import product
import requests, re, json
# import system time module for specific delay to avoid being blocked
# import time
# main data crawl parser class for HTML content
from bs4 import BeautifulSoup
# database connection
from db_connection import get_connection


## append product type and page Number for page list
## the product category for first API are : hair, make-up, face and body
API_LISTING_PAGE_01 = 'https://www.lookfantastic.com.sg/health-beauty/{}/5-star-products.list?pageNumber={}&sortOrder=salesRank'

## the product category for second API is : men
API_LISTING_PAGE_02 = 'https://www.lookfantastic.com.sg/health-beauty/{}/top-rated-products.list?pageNumber={}&sortOrder=salesRank'

def getTheLastPage(url):
    #print(url)
    res = requests.get(url)
    html = "".join(line.strip() for line in res.text.split("\n"))
    soup = BeautifulSoup(html, 'html.parser')
    last_page = soup.find('a', {'class':'responsivePaginationButton responsivePageSelector responsivePaginationButton--last'})
    
    #print(last_page)
    if last_page is not None:
        #print(last_page.contents[0])
        return int(last_page.contents[0])
    else:
        #print(1)
        return 1
        
API_CATEGORY_01 = ['hair', 'make-up', 'face', 'body']
API_CATEGORY_02 = ['men']

import math

def pullList(category, category_name):
    
    if category_name in API_CATEGORY_01:
        API_LISTING_PAGE = API_LISTING_PAGE_01
    else:
        API_LISTING_PAGE = API_LISTING_PAGE_02
        
    start_page = 1
    
    ## from the first page list, get the number of pages for this category, then get the num of pages to pull 
    url = API_LISTING_PAGE.format(category_name, start_page)
    
    num_of_pages = getTheLastPage(url)
    
    if num_of_pages > 5:
        last_pages_to_pull = max(5, math.ceil(num_of_pages * 0.4))
    else:
        last_pages_to_pull = num_of_pages
        
    ## from the first page to the last page to pull, pull them one by one
    
    href_list = []
    
    for num in range(1, last_pages_to_pull + 1, 1):
        url = API_LISTING_PAGE.format(category_name, num)
        res = requests.get(url)
        html = "".join(line.strip() for line in res.text.split("\n"))
        soup = BeautifulSoup(html, 'html.parser')
        
        product_list = soup.find_all('a', {'class':'productBlock_link'})
        
        #print(product_list)
        
        for product in product_list:
            if product['href'] not in href_list:
                href_list.append(product['href'])
            
    return [
            {
                'product_category' : category, 
                 'link' : 'https://www.lookfantastic.com.sg' + href
            }
            for href in href_list
            ]
            
            
def pullItem(category, category_name, product_link, conn, cur):
    url = product_link
    res = requests.get(url)
    
    html = "".join(line.strip() for line in res.text.split("\n"))
    soup = BeautifulSoup(html, 'html.parser')
    
    product_id = getProductId(url)
    
    #print('product id is ', product_id)
    
    image = getProductImage(soup)
    
    #print('image url is ', image)
    
    product_name = getProductName(soup)
    
    #print("url link is ", url)
    
    #print('product name is ', product_name)
    
    product_overview = getProductOverview(soup)
    
    #print('product overview is ', product_overview)
    
    product_direction = getDirections(soup)
    
    #print('product direction is ', product_direction)
    
    num_of_review = getReviews(soup)
    
    #print("num of reivew is ", num_of_review)
    
    rating = getRating(soup)
    
    #print('rating is ', rating)
    
    price = getPrice(soup)
    
    rrp = getRRP(soup)
    
    if rrp is None:
        rrp = price
    
    #print("RRP is {}, and price is {}".format(rrp, price))
    
    #print("------------------------------------------------------")
    
    cur.execute("select 1 from data.look_fantastic_product where product_id = %s", (product_id, ))
    p = cur.fetchone()
    
    if p is None:
        # new product
        cur.execute(
        """
            insert into data.look_fantastic_product (product_id, product_category, product_link, product_image, product_name, product_overview, product_direction, reviews, ratings, product_rrp, product_sell_price, last_update)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, current_timestamp)
        """, (product_id, category, url, image, product_name, product_overview, product_direction, num_of_review, rating, rrp, price)
        )
    else:
        # updating existing
        cur.execute(
        """
                update data.look_fantastic_product
                set product_category = %s,
                    product_link = %s,
                    product_image = %s,
                    product_name = %s,
                    product_overview = %s,
                    product_direction = %s,
                    reviews = %s,
                    ratings = %s,
                    product_rrp = %s,
                    product_sell_price = %s,
                    last_update = current_timestamp
                where product_id = %s
            """, (category, url, image, product_name, product_overview, product_direction, num_of_review, rating, rrp, price, product_id)

        )
        
    conn.commit()
    
    return
    
    
def getProductId(url):
    
    product_id_temp = url.split('/')[-1]
    product_id = product_id_temp.replace('.html', '')
    
    if product_id is None or len(product_id) == 0:
        return None
    else:
        return int(product_id)
        
def getProductImage(soup):
    image_block = soup.find('img', {'class':'athenaProductImageCarousel_image'})
    if image_block is None:
        return 'NA'
    
    return image_block['src']
    
def getProductName(soup):
    name_block = soup.find('h1', {'class':'productName_title'})
    if name_block is None:
        return 'NA'
    else:
        product_name = name_block.contents[0]
    
    return product_name
    
def getProductOverview(soup):
    
    overview_block = soup.find('div', {'id':'product-description-content-lg-2'})
    if overview_block is None:
        return 'NA'
    overview_temp = overview_block.findChildren('div', {'class':'productDescription_synopsisContent'})[0].findChildren('p')
    overview_string = str(overview_temp)
    overview_string = overview_string.replace('<p>', '')
    overview_string = overview_string.replace('</p>', '')
    overview_string = overview_string.replace('<strong>', '')
    overview_string = overview_string.replace('</strong>', '')
    overview_string = overview_string.replace('<br/>', '; ')
    overview_string = overview_string.replace('[', '')
    overview_string = overview_string.replace(']', '')
    overview_string = overview_string.replace('<EM>', '')
    overview_string = overview_string.replace('</EM>', '')
    
    return overview_string
    
def getDirections(soup):
    
    direction_block = soup.find('div', {'id':'product-description-content-lg-15'})
    if direction_block is None:
        return 'NA'
    
    direction_temp = direction_block.findChildren('div', {'class':'productDescription_synopsisContent'})[0].findChildren('p')
    direction_string = str(direction_temp)
    direction_string = direction_string.replace('<p>', '')
    direction_string = direction_string.replace('</p>', '')
    direction_string = direction_string.replace('<strong>', '')
    direction_string = direction_string.replace('</strong>', '')
    direction_string = direction_string.replace('<br/>', '; ')
    direction_string = direction_string.replace('[', '')
    direction_string = direction_string.replace(']', '')
    direction_string = direction_string.replace('<EM>', '')
    direction_string = direction_string.replace('</EM>', '')
    
    return direction_string
    
def getReviews(soup):
    review_block = soup.find('p', {'class':'athenaProductReviews_reviewCount Auto'})
    if review_block is None:
        return 0
    
    review_block_content = review_block.contents[0]
    
    num_of_review = review_block_content.split(" ")[0]
    
    return float(num_of_review)
    
def getRating(soup):
    rating_block = soup.find('span', {'class':'athenaProductReviews_aggregateRatingValue'})
    if rating_block is None:
        return 0
    
    rating_value = rating_block.contents[0]
    
    return float(rating_value)
    
def extractPriceFromString(inputString):
    
    value = inputString.lower()
    value = value.replace('$', '')
    value = value.replace('s', '')
    
    return float(value)
    
def getRRP(soup):
    rrp_block = soup.find('p', {'class':'productPrice_rrp'})
    if rrp_block is None:
        return None
    
    rrp_value = rrp_block.contents[0].split(" ")[-1]
    
    rrp_value = extractPriceFromString(rrp_value)
    
    return rrp_value
    
def getPrice(soup):
    price_block = soup.find('p', {'class':'productPrice_price'})
    if price_block is None:
        return 0
    
    price_value = price_block.contents[0].lower()
    
    price_value = extractPriceFromString(price_value)
    
    return float(price_value)
    
def main():

    # main entry method for crawling i-herb data from web
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("set search_path = data")

    
    ## categories to be pulled from the LookFantastic website
    categories = [
        ('Hair', 'hair'),
        ('Makeup', 'make-up'),
        ('Face', 'face'),
        ('Body', 'body'),
        ('Men', 'men')
    ]
    
    for c in categories:
        print(c)
        product_link_list = pullList(c[0], c[1])
        
        #print(product_link_list)
        print("number of product is ", len(product_link_list))
        for product_link in product_link_list:
            pullItem(c[0], c[1], product_link['link'], conn, cur)
            
            
if __name__ == "__main__":
    main()
