create table activities (
    id varchar(50) not null,
    name varchar(50) not null,
    created_at real not null,
    begin_date real not null,
    end_date real not null,
    state varchar(10) not null,
    creator_name varchar(50),
    creator varchar(50) not null,
    key idx_created_at (created_at),
    primary key (id)
) engine=innodb default charset=utf8;

create table gifts (
    id varchar(50) not null,
    name varchar(50) not null,
    image varchar(300) not null,
    activity_id varchar(50) not null,
    created_at real not null,
    key idx_created_at (created_at),
    primary key (id)
) engine=innodb default charset=utf8;

create table user_gifts (
    id varchar(50) not null,
    user_id varchar(50) not null,
    activity_id varchar(50) not null,
    gift_id varchar(50) not null,
    created_at real not null,
    key idx_created_at (created_at),
    primary key (id)
) engine=innodb default charset=utf8;

create table budgets (
    id varchar(50) not null,
    name varchar(50) not null,
    creator varchar(50) not null,
    creator_name varchar(50) not null,
    created_at real not null,
    state varchar(10) not null,
    key idx_created_at (created_at),
    primary key (id)
) engine=innodb default charset=utf8;

create table user_budgets (
    id varchar(50) not null,
    user_id varchar(50) not null,
    user_name varchar(50) not null,
    user_email varchar(50) not null,
    budget_id varchar(50) not null,
    budget_type varchar(50) not null,
    budget_fee real(9,2) not null,
    created_at real not null,
    key idx_created_at (created_at),
    primary key (id)
) engine=innodb default charset=utf8;