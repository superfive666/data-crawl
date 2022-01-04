-- shopee data crawl tables
create table if not exists data.shopee_data (
	match_id numeric(11,0) not null,
	match_text character varying (200) not null,
	sort_by character varying (15) not null,
	shop_id numeric(11,0) not null,
	item_id numeric(11,0) not null
);
grant insert, update, delete, select on data.shopee_data to data_app_role;

create table if not exists data.shopee_shop (
	shop_id numeric(11,0) primary key,
	shop_name character varying (100),
	shop_acc character varying (50) not null,
	shop_portrait character varying (50) not null,
	shop_addr character varying (200) not null
);
grant insert, update, delete, select on data.shopee_shop to data_app_role;

create table if not exists data.shopee_item (
	item_id numeric (11,0) primary key,
	item_name character varying (300) not null,
	item_url character varying (1000) not null,
	item_image character varying (300) not null,
	item_description character varying (5000) not null,
	rating_count numeric(8,0) not null,
	ratings numeric(6,2) not null,
	sold numeric(19,0) not null,
	last_update timestamp not null
);
grant insert, update, delete, select on data.shopee_item to data_app_role;

create table if not exists data.shopee_item_model (
	model_id numeric (19,0) primary key,
	item_id numeric (11,0),
	model_name character varying (50) default 'default' not null,
	price_before money not null,
	price_after money not null,
	last_update timestamp not null,
	constraint fk_shopee_item
	foreign key(item_id) references data.shopee_item (item_id) 
	on delete cascade
);
grant insert, update, delete, select on data.shopee_item_model to data_app_role;

-- iheard data crawl tables
create table if not exists data.iherb_product (
  product_id numeric(19,0) primary key,
  product_category character varying (100) not null,
  product_link character varying (1000) not null,
  product_path character varying (1000) not null,
  product_image character varying (300) not null,
  product_brand character varying (100) default 'NA' not null,
  product_name character varying (500) default 'NA' not null,
  product_rank character varying (2000),
  product_overview character varying (10000),
  reviews numeric(7,0) default 0 not null,
  ratings numeric(6,2) default 0 not null,
  last_update timestamp default current_timestamp not null
);
grant insert, update, delete, select on data.iherb_product to data_app_role;

create table if not exists data.iherb_model (
  product_id numeric(19,0),
  model_name character varying (500) default 'default' not null,
  price_before money default 0 not null,
  price_after money default 0 not null,
  constraint fk_iherb_product
  foreign key(product_id) references data.iherb_product (product_id)
  on delete cascade
);
grant insert, update, delete, select on data.iherb_model to data_app_role;