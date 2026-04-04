INSERT INTO auth_users (username, password_hash, display_name, status)
VALUES ('admin', '$2b$10$ydMkvQ83zoqHxjJmCcviaupmIqse4rfj3k2eujOWeQgitZoSil05a', 'System Admin', 'active');

INSERT INTO model_registry (model_name, model_type, service_name, status)
VALUES
('UniPic-2', 'generation', 'python-ai-service', 'active'),
('Electric-Score-v1', 'scoring', 'python-ai-service', 'active');

INSERT INTO model_prompt_templates (template_name, scene_type, positive_prompt, negative_prompt)
VALUES
('Wind Farm Baseline', 'wind-farm', 'A modern wind turbine farm at sunset', 'blurry, deformed, low quality');
