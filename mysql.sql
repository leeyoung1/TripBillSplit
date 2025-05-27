CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    nickname VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(255) NULL,
    phone VARCHAR(50) UNIQUE NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
		deleted BOOLEAN DEFAULT FALSE
);

-- -----------------------------------------------------
-- Table `trips` (旅游表)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `trips` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NULL,
  `budget` DECIMAL(10,2) NULL,
  `cover_image_url` VARCHAR(255) NULL,
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '旅行状态: 1:planned, 2:active, 3:ended, 4:cancelled',
  `creator_id` INT NOT NULL COMMENT '逻辑关联 users.id',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '逻辑删除标记: FALSE未删除, TRUE已删除',
  PRIMARY KEY (`id`))
ENGINE = InnoDB
COMMENT = '旅游表';


-- -----------------------------------------------------
-- Table `trip_members` (旅游人员表)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `trip_members` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `trip_id` INT NOT NULL COMMENT '逻辑关联 trips.id',
  `user_id` INT NOT NULL COMMENT '逻辑关联 users.id',
  `role` TINYINT NOT NULL COMMENT '成员角色: 1:owner, 2:admin, 3:editor, 4:member',
  `status` TINYINT NOT NULL DEFAULT 2 COMMENT '成员状态: 1:active, 2:invited, 3:pending_owner_approval',
  `joined_at` DATETIME NULL COMMENT '成员实际加入或变为active的时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '逻辑删除标记: FALSE未删除, TRUE已删除',
  PRIMARY KEY (`id`))
ENGINE = InnoDB
COMMENT = '旅游人员表';

-- -----------------------------------------------------
-- Table `trip_invitations` (旅游邀请表)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `trip_invitations` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `trip_id` INT NOT NULL COMMENT '逻辑关联 trips.id',
  `token` VARCHAR(255) NOT NULL COMMENT '邀请令牌',
  `created_by_user_id` INT NOT NULL COMMENT '逻辑关联 users.id',
  `expires_at` DATETIME NULL COMMENT '过期时间',
  `max_uses` INT NULL DEFAULT 1 COMMENT '最大使用次数',
  `current_uses` INT NOT NULL DEFAULT 0 COMMENT '当前使用次数',
  `role_to_assign` TINYINT NOT NULL DEFAULT 4 COMMENT '被邀请者将获得的角色: 例如 4=member',
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否活跃',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '逻辑删除标记: FALSE未删除, TRUE已删除',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `token_UNIQUE` (`token` ASC))
ENGINE = InnoDB
COMMENT = '旅游邀请表';