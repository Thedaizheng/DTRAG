CREATE TABLE IF NOT EXISTS `doc` (
  `id`       bigint NOT NULL AUTO_INCREMENT COMMENT '文档id',
  `name`     varchar(100) NOT NULL DEFAULT '' COMMENT '文档名称',
  `doc_group`    varchar(100) NOT NULL DEFAULT '' COMMENT '文档组',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `name_index` (`name`) 
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '文档表';

CREATE TABLE IF NOT EXISTS `doc_ver` (
  `id`       bigint NOT NULL AUTO_INCREMENT COMMENT '文档版本id',
  `doc_id`   varchar(100) NOT NULL DEFAULT '' COMMENT '文档ID',
  `status`   smallint NOT NULL DEFAULT -1 COMMENT '0表示草稿，1表示发布',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '文档版本表';

CREATE TABLE IF NOT EXISTS `doc_group_permission` (
  `id`            bigint NOT NULL AUTO_INCREMENT COMMENT '文档权限id',
  `doc_group`     varchar(50) NOT NULL DEFAULT '' COMMENT '文档ID',
  `allowed_users` varchar(500) NOT NULL DEFAULT '' COMMENT '权限，需要设置可访问的用户，如果为*表示都可以访问，如果为 -user则表示不可访问，user表示可访问，比如, "*,-123"表示都可以访问，但是123用户不可以访问',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `doc_group_index` (`doc_group`) 
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '文档权限表';

CREATE TABLE IF NOT EXISTS `doc_nodes` (
  `id`         bigint NOT NULL COMMENT '节点id',
  `doc_id`     bigint NOT NULL DEFAULT -1 COMMENT '文档ID',
  `doc_ver_id` bigint NOT NULL DEFAULT -1 COMMENT '文档版本表的ID',
  `parent_id`  bigint NOT NULL DEFAULT -1 COMMENT '从属的父节点ID',
  `level`      smallint NOT NULL DEFAULT 0 COMMENT '层级，父节点层级为0',
  `seq`        smallint NOT NULL DEFAULT 0 COMMENT '同一父节点、同一层级下的，排序',
  `content`    varchar(2000) NOT NULL DEFAULT '' COMMENT '数据节点的内容',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '文档节点表';

CREATE TABLE IF NOT EXISTS `doc_nodes_da` (
  `id`           bigint NOT NULL AUTO_INCREMENT COMMENT '节点id',
  `doc_nodes_id` bigint NOT NULL DEFAULT -1 COMMENT '文档节点表的ID',
  `content`      varchar(2000) NOT NULL DEFAULT '' COMMENT '数据增强的内容',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '文档节点数据增强表';
