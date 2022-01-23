from numpy import product
import requests, re, json
# import system time module for specific delay to avoid being blocked
import time
# main data crawl parser class for HTML content
from bs4 import BeautifulSoup

from db_connection import get_connection

## best seller page. 
BEST_SELLER_PAGE_01 = "https://sg.althea.kr/collections/best-seller?sort=manual"

## the rest best seller pages
BEST_SELLER_PAGE_02 = "https://sg.althea.kr/collections/best-seller?page={}&sort=manual"

seconds = 3

def getTheLastPage(url):
    #print(url)
    res = requests.get(url, time.sleep(seconds))
    #time.sleep(5)
    html = "".join(line.strip() for line in res.text.split("\n"))
    soup = BeautifulSoup(html, 'html.parser')
    page_list = soup.find_all('div', {'class':'Grid__Cell 1/2--phone 1/3--tablet-and-up 1/4--lap-and-up'})
    
    page_list_01 = soup.find_all('a', {'class':'Pagination__NavItem Link Link--primary'})
    
    last_page_index = page_list_01[-2].contents[0]
    
    print("The last page number is ", last_page_index)
    
    return int(last_page_index)
    

### for each page, get the items one by one
def getItemUrlFromPage(page_url):
    print("getting items from page ", page_url)
    res = requests.get(page_url, time.sleep(seconds))
    
    html = "".join(line.strip() for line in res.text.split("\n"))
    soup = BeautifulSoup(html, 'html.parser')
    page_item_list = soup.find_all('div', {'class':'Grid__Cell 1/2--phone 1/3--tablet-and-up 1/4--lap-and-up'})
    
    item_url_list = []
    
    #print("There are {} items in this page".format(len(page_item_list)))
    
    for page_item in page_item_list:
        #print(page_item)
        temp_item = page_item.findChildren('a', {'class':'ProductItem__ImageWrapper'})
        
        item_url = temp_item[0]['href']
        
        #print(item_url)
        
        temp_id = page_item.findChildren('div', {'class':'AddToBag'})
        
        product_id = temp_id[0]['productid']
        #print(product_id)
        
        item_url_list.append([item_url, product_id])
    return item_url_list
    
def getItemUrlFromAllPages(num_of_page):
    item_url_id_list_all = [] 
    for i in range(1, (num_of_page + 1)):
        if i == 1:
            page_url = BEST_SELLER_PAGE_01
        else:
            page_url = BEST_SELLER_PAGE_02.format(i)
            
        page_url_id_list = getItemUrlFromPage(page_url)
        
        for url_and_id in page_url_id_list:
            complete_url = 'https://sg.althea.kr' + url_and_id[0]
            product_id = url_and_id[1]
            item_url_id_list_all.append([complete_url, product_id])
            
    return item_url_id_list_all
    
    
def getProductImage(soup):
    image_block = soup.find('div', {'class':'Product__SlideItem Product__SlideItem--image Carousel__Cell is-selected'})
    #print('image block is ', image_block)
    if image_block is None:
        return 'NA'
    else:
        image_sub_block = image_block.findChildren('img', {'class' : 'Image--lazyLoad Image--fadeIn'})
        
        if image_sub_block is None or len(image_sub_block) == 0:
            return 'NA'
        else:
            #print(image_sub_block)
            image_url = "https:" + image_sub_block[0]['data-original-src']
            return image_url

def getProductBrand(soup):
    meta_block = soup.find('h2', {'class':'ProductMeta__Vendor Heading u-h6 deskContent'})
    if meta_block is None:
        return 'NA'
    else:
        temp_item = meta_block.findChildren('a')
        if temp_item is None or len(temp_item) == 0:
            return meta_block.contents[0]
        else:
            #print("product brand is ", temp_item)
            return temp_item[0].contents[0]
        
    
def getProductName(soup):
    temp_block = soup.find('h1', {'class':'ProductMeta__Title Heading u-h2'})
    if temp_block is None:
        return 'NA'
    else:
        return temp_block.contents[0]
    
def getProductDesc(soup):
    html_content = str(soup)
    
    start_index = html_content.find("<short_description>")
    
    end_index = html_content.find("</short_description>")
    
    #print("start index is {}, end index is {}".format(start_index, end_index))
    if end_index <= start_index:
        return 'NA'
    else:
        product_desc = html_content[start_index : end_index]
        
        product_desc = product_desc.replace("<short_description>", "")
    
        #print(product_desc)
        return product_desc
    
def getProductReview(soup):
    temp_block = soup.find('div', {'class':'jdgm-rev-widg__summary-text'})
    if temp_block is None:
        return 0
    else:
        temp_str = temp_block.contents[0]
        price_str = temp_str.split(" ")[2]
        if price_str.isnumeric():
            return int(price_str)
        else:
            return 0
    
def getSalePrice(soup):
    temp_block = soup.find('div', {'class':'ProductMeta__PriceList Heading'})
    if temp_block is None:
        return 'NA'
    else:
        temp_str = temp_block.findChildren('span', {'class':'ProductMeta__Price Price Price--highlight Text--subdued u-h4'})
        
        if temp_str is None or len(temp_str) == 0:
            temp_str = temp_block.findChildren('span', {'class':'ProductMeta__Price Price Text--subdued u-h4'})
        price_str = temp_str[-1].contents[0]
        price_str = price_str.replace("S$", '')
        
        return float(price_str)
    
def getOriginalPrice(soup):
    temp_block = soup.find('div', {'class':'ProductMeta__PriceList Heading'})
    if temp_block is None:
        return None
    else:
        temp_str = temp_block.findChildren('span', {'class':'ProductMeta__Price Price Price--compareAt Text--subdued u-h4'})
        if temp_str is None or len(temp_str) == 0:
            return None
        
        price_str = temp_str[0].contents[0]
        price_str = price_str.replace("S$", '')
        
        return float(price_str)
        
        
def pullItem(product_url, product_id, conn, cur):
    res = requests.get(product_url)
    
    html = "".join(line.strip() for line in res.text.split("\n"))
    soup = BeautifulSoup(html, 'html.parser')
    
    
    product_image = getProductImage(soup)
    
    product_brand = getProductBrand(soup)
    
    product_name = getProductName(soup)
    
    product_desc = getProductDesc(soup)
    
    product_review = getProductReview(soup)
    
    product_sell_price = getSalePrice(soup)
    
    product_original_price = getOriginalPrice(soup)
    
    if product_original_price is None:
        product_original_price = product_sell_price
    
    #print("productId is ", product_id)
    
    #print("product_image is ", product_image)
    
    #print("product_brand is ", product_brand)
    
    #print("product_name is ", product_name)
    
    #print("product_desc is ", product_desc)
    
    #print("product_review is ", product_review)
    
    #print("product_sell_price is ", product_sell_price)
    
    #print("product_original_price is ", product_original_price)
    
    cur.execute("select 1 from data.althea_product where product_id = %s", (product_id, ))
    p = cur.fetchone()
    
    if p is None:
        # new product
        cur.execute(
        """
            insert into data.althea_product (product_id, product_link, product_image, product_brand, product_name, product_description, reviews, product_sell_price, product_original_price, last_update)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, current_timestamp)
        """, (product_id, product_url, product_image, product_brand, product_name, product_desc, product_review, product_sell_price, product_original_price)
        )
    else:
        # updating existing
        cur.execute(
        """
                update data.althea_product
                set 
                    product_link = %s,
                    product_image = %s,
                    product_brand = %s,
                    product_name = %s,
                    product_description = %s,
                    reviews = %s,
                    product_sell_price = %s,
                    product_original_price = %s,
                    last_update = current_timestamp
                where product_id = %s
            """, (product_url, product_image,product_brand, product_name, product_desc, product_review, product_sell_price, product_original_price, product_id)

        )
        
    conn.commit()
    
    return

def main():

    # main entry method for crawling althea data from web
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("set search_path = data")
    
    num_of_page = getTheLastPage(BEST_SELLER_PAGE_01)
    
    complete_url_id_list = getItemUrlFromAllPages(num_of_page)
    
    for i in range(len(complete_url_id_list)):
        print("item index is {}".format(i))
        url, product_id = complete_url_id_list[i][0], complete_url_id_list[i][1]
        #print(url)
        pullItem(url, product_id, conn, cur)
    
    print("Completed crawling for {} items".format(len(complete_url_id_list)) )

if __name__ == "__main__":
    main()