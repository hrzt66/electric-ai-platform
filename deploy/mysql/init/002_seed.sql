INSERT INTO auth_users (username, password_hash, display_name)
VALUES ('admin', '$2a$10$MVsC0z7o3g8X9h9O0uHkXee4g0S6g5n8J2zM6W7Wm2mM5sV2uQ9O6', '系统管理员');

INSERT INTO model_registry (model_name, model_type, service_name, status)
VALUES
('UniPic-2', 'generation', 'python-ai-service', 'active'),
('Electric-Score-v1', 'scoring', 'python-ai-service', 'active');

INSERT INTO model_prompt_templates (template_name, scene_type, positive_prompt, negative_prompt)
VALUES
('风电场基础模板', 'wind-farm', 'A modern wind turbine farm at sunset', 'blurry, deformed, low quality');
