create table data.shopee_data (
	match_id numeric(11,0) not null,
	match_text character varying (200) not null,
	sort_by character varying (15) not null,
	shop_id numeric(11,0) not null,
	item_id numeric(11,0) not null
);

create table data.shopee_shop (
	shop_id numeric(11,0) primary key,
	shop_name character varying (100),
	shop_acc character varying (50) not null,
	shop_portrait character varying (50) not null,
	shop_addr character varying (200) not null
);

create table data.shopee_item (
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

create table data.shopee_item_model (
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
