CREATE TABLE `events` (
	`id` int AUTO_INCREMENT NOT NULL,
	`event_id` varchar(64) NOT NULL,
	`user_id` varchar(64) NOT NULL,
	`session_id` varchar(64) NOT NULL,
	`event_type` varchar(32) NOT NULL,
	`event_time` timestamp NOT NULL,
	`product_id` varchar(64) NOT NULL,
	`category_id` varchar(64) NOT NULL,
	`brand` varchar(128) NOT NULL,
	`price` decimal(10,2) NOT NULL,
	`quantity` int NOT NULL DEFAULT 1,
	`page_url` text NOT NULL,
	`referrer` text,
	`device_type` varchar(32) NOT NULL,
	`payload_json` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `events_id` PRIMARY KEY(`id`),
	CONSTRAINT `events_event_id_unique` UNIQUE(`event_id`)
);
--> statement-breakpoint
CREATE TABLE `products` (
	`id` int AUTO_INCREMENT NOT NULL,
	`product_id` varchar(64) NOT NULL,
	`sku` varchar(64) NOT NULL,
	`name` text NOT NULL,
	`category_id` varchar(64) NOT NULL,
	`brand` varchar(128) NOT NULL,
	`price` decimal(10,2) NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `products_id` PRIMARY KEY(`id`),
	CONSTRAINT `products_product_id_unique` UNIQUE(`product_id`)
);
--> statement-breakpoint
CREATE TABLE `sessions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`session_id` varchar(64) NOT NULL,
	`user_id` varchar(64) NOT NULL,
	`device_type` varchar(32) NOT NULL,
	`start_time` timestamp NOT NULL DEFAULT (now()),
	`end_time` timestamp,
	`event_count` int NOT NULL DEFAULT 0,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `sessions_id` PRIMARY KEY(`id`),
	CONSTRAINT `sessions_session_id_unique` UNIQUE(`session_id`)
);
