CREATE TABLE auth_users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE model_registry (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    model_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(32) NOT NULL,
    service_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    description TEXT NULL,
    default_positive_prompt TEXT NULL,
    default_negative_prompt TEXT NULL,
    local_path TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_model_registry_model_name (model_name)
);

CREATE TABLE model_prompt_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    template_name VARCHAR(255) NOT NULL,
    scene_type VARCHAR(64) NOT NULL,
    positive_prompt TEXT NOT NULL,
    negative_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE task_jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    stage VARCHAR(32) NOT NULL DEFAULT 'queued',
    model_name VARCHAR(128) NOT NULL,
    prompt TEXT NULL,
    negative_prompt TEXT NULL,
    payload_json LONGTEXT NOT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE asset_images (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_id BIGINT NOT NULL,
    image_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'generated',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_asset_images_job_id (job_id),
    CONSTRAINT fk_asset_images_job FOREIGN KEY (job_id) REFERENCES task_jobs(id)
);

CREATE TABLE asset_image_prompts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    image_id BIGINT NOT NULL,
    positive_prompt TEXT NOT NULL,
    negative_prompt TEXT NULL,
    sampling_steps INT NOT NULL,
    seed BIGINT NOT NULL,
    guidance_scale DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_asset_image_prompts_image FOREIGN KEY (image_id) REFERENCES asset_images(id) ON DELETE CASCADE
);

CREATE TABLE asset_image_scores (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    image_id BIGINT NOT NULL,
    visual_fidelity DECIMAL(5,2) NOT NULL,
    text_consistency DECIMAL(5,2) NOT NULL,
    physical_plausibility DECIMAL(5,2) NOT NULL,
    composition_aesthetics DECIMAL(5,2) NOT NULL,
    total_score DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_asset_image_scores_image FOREIGN KEY (image_id) REFERENCES asset_images(id) ON DELETE CASCADE
);

CREATE TABLE audit_task_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_id BIGINT NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    message TEXT NULL,
    payload_json LONGTEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_task_events_job_id (job_id),
    CONSTRAINT fk_audit_task_events_job FOREIGN KEY (job_id) REFERENCES task_jobs(id)
);
