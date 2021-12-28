import requests, json, time
from db_connection import get_connection


IMAGE_BASE_URL = "https://cf.shopee.sg/file/"
# match_id? newest? by? scenario (PAGE_OTHERS | PAGE_COLLECTION)? page_type (search | colection)?
API_SEARCH_ITEMS = "https://shopee.sg/api/v4/search/search_items?&limit=60&&order=desc&version=2"
# itemid? shopid?
API_GET_ITEM_DETAILS = "https://shopee.sg/api/v4/item/get?"
# shopid?
API_GET_SHOP_INFO = "https://shopee.sg/api/v4/product/get_shop_info?"



def insert_shop(shop_id: int, conn, cur):
    cur.execute('select 1 from shopee_shop where shop_id = %s', (shop_id,))
    shop = cur.fetchone()
    if shop is not None:
        return
    
    url = API_GET_SHOP_INFO + '&shopid={}'.format(shop_id)
    res = requests.get(url)
    data = json.loads(res.text)['data']

    if data is None:
        return
    
    cur.execute(
        """
            insert into shopee_shop (shop_id, shop_name, shop_acc, shop_portrait, shop_addr)
            values (%s, %s, %s, %s, %s)
        """, (shop_id, data['name'], data['account']['username'], data['account']['portrait'], data['place'])
    )
    conn.commit() 


def insert_item_model(detail: dict, conn, cur):
    model_id = detail['modelid']
    cur.execute('select 1 from shopee_item_model where model_id = %s', (model_id,))
    model = cur.fetchone()

    # populate default names for the missing model names 
    if detail['name'] == '':
        detail['name'] = 'default'


    if model is None:
        # inser new
        cur.execute(
            """
                insert into shopee_item_model(model_id, item_id, model_name, price_before, price_after, last_update)
                values (%s, %s, %s, %s, %s, current_timestamp)
            """, (model_id, detail['itemid'], detail['name'], detail['price_before_discount']/100000, detail['price']/100000)
        )
    else:
        # update with the newest information
        cur.execute(
            """
                update shopee_item_model
                set model_name = %s,
                    price_before = %s,
                    price_after = %s,
                    last_update = current_timestamp
                where model_id = %s
            """, (detail['name'], detail['price_before_discount']/100000, detail['price']/100000, model_id)
        )
    
    conn.commit()


def get_item_url(name: str, shopid, itemid):
    """
        Item URL is directly related to the item name
        - replace space with dash "-"
        - replace bracket with dash "-"
        - remove special characters "%", "/" etc.
    """
    name = name.replace(' ', '-')
    name = name.replace('[', '-')
    name = name.replace(']', '-')
    name = name.replace('(', '')
    name = name.replace(')', '')
    name = name.replace('%', '')
    name = name.replace('/', '-')
    name = name.replace('--', '-')
    return 'https://shopee.sg/{}-i.{}.{}'.format(name, shopid, itemid)


def get_path(item: dict):
    return '>'.join([i['display_name'] for i in item['fe_categories']])


def insert_item(item: dict, conn, cur):
    item_id = item['itemid']
    cur.execute('select 1 from shopee_item where item_id = %s', (item_id,))
    it = cur.fetchone()
    
    if item['brand'] is None:
        item['brand'] = 'NA'

    if item['description'] is None:
        item['description'] = 'NA'

    if it is None:
        # insert new
        cur.execute(
            """
                insert into shopee_item(item_id, item_name, item_url, item_image, item_description, path, brand, rating_count, ratings, sold, last_update)
                values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, current_timestamp)
            """, (item_id, item['name'], get_item_url(item['name'], item['shopid'], item_id), item['image'], item['description'], get_path(item), item['brand'], item['item_rating']['rating_count'][0], round(item['item_rating']['rating_star'], 2), item['sold'] + item['historical_sold']) 
        )
    else:
        # update with the latest information
        cur.execute(
            """
                update shopee_item
                set item_name = %s,
                    item_url = %s,
                    item_image = %s,
                    item_description = %s,
                    rating_count = %s,
                    ratings = %s,
                    sold = %s,
                    last_update = current_timestamp
                where item_id = %s
            """, (item['name'], get_item_url(item['name'], item['shopid'], item_id), item['image'], item['description'], item['item_rating']['rating_count'][0], round(item['item_rating']['rating_star'], 2), item['sold'] + item['historical_sold'], item_id)
        )

    conn.commit()


def process_item(shop_id: int, item_id: int, conn, cur):
    url = API_GET_ITEM_DETAILS + 'shopid={}'.format(shop_id) + '&itemid={}'.format(item_id)
    res = requests.get(url)
    data = json.loads(res.text)['data']
    
    insert_item(data, conn, cur)

    print("Item", data['itemid'], data['name'], 'has', len(data['models']), 'models')

    for m in data['models']:
        insert_item_model(m, conn, cur)
    

def process_record(match_id: int, match_text: str, sort: str, record: dict, conn, cur):
    shopid = record['item_basic']['shopid']
    insert_shop(shopid, conn, cur)

    itemid = record['item_basic']['itemid']
    process_item(shopid, itemid, conn, cur)

    cur.execute(
        """
            select 1 from shopee_data
            where match_id = %s
              and sort_by = %s
              and shop_id = %s
              and item_id = %s
        """, (match_id, sort, shopid, itemid)
    )

    dd = cur.fetchone()
    if dd is not None:
        # already recorded before
        return

    cur.execute(
        """
            insert into shopee_data(match_id, match_text, sort_by, shop_id, item_id)
            values (%s, %s, %s, %s, %s)
        """, (match_id, match_text, sort, shopid, itemid)
    )

    conn.commit()


def pull(match_id: int, match_text: str, by: str, conn, cur):
    """
        Options for by:
        - relevance: "Popular"
        - ctime: "Latest"
        - sales: "Top Sales"
    """
    start = 0
    while True:
        print("Pressing", match_id, "by", by, "start", start)
        scenario = 'PAGE_COLLECTION'
        ptype = 'collection'
        if match_id > 10000000:
            scenario = 'PAGE_OTHERS'
            ptype = 'search'

        url = API_SEARCH_ITEMS + "&match_id={}".format(match_id) + "&newest={}".format(start) + "&by={}".format(by) + "&scenario={}".format(scenario) + "&page_type={}".format(ptype)
        res = requests.get(url)
        data = json.loads(res.text)['items']

        if data is None:
            return

        start += 60
        for d in data:
            process_record(match_id, match_text, by, d, conn, cur)
            # prevent being blocked from spamming requests 
            # time.sleep(1)

        if len(data) < 60 or start > 300:
            # stop when no more data coming from this page
            break
 

def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('set search_path = data')

    match_ids = [
        (886564, 'Fight Maskne'),
        (885923, 'Acne Prone Skin'),
        (886669, 'Combination Skin'),
        (885724, 'Dry Skin'),
        (886250, 'Oily Skin'),
        (885713, 'Sensitive Skin'),
        (11012444, 'Women Hair Care'),
        (11012427, 'Skin Care'),
        (11012407, 'Oral Care'),
        (11012399, 'Nails'),
        (11012390, 'Men Grooming'),
        (11012375, 'Makeup'),
        (11012351, 'Fragrances'),
        (11012345, 'Feminine Care'),
        (11012302, 'Bath & Body')
    ]
    by = ['relevance', 'ctime', 'sales']

    for m in match_ids:
        for b in by:
            pull(m[0], m[1], b, conn, cur)


if __name__ == "__main__":
    main()
