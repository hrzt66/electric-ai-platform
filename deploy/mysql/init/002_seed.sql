INSERT INTO auth_users (username, password_hash, display_name, status)
VALUES ('admin', '$2b$10$ydMkvQ83zoqHxjJmCcviaupmIqse4rfj3k2eujOWeQgitZoSil05a', 'System Admin', 'active');

INSERT INTO model_registry (model_name, display_name, model_type, service_name, status, description, default_positive_prompt, default_negative_prompt, local_path)
VALUES
('sd15-electric', 'Stable Diffusion 1.5 Electric', 'generation', 'python-ai-service', 'available', 'SD1.5 baseline generation runtime for electric scenes', '500kV substation, industrial realism, detailed power equipment', 'blurry, low quality, disconnected wires, deformed insulators', 'G:\\electric-ai-runtime\\models\\generation\\sd15-electric'),
('unipic2-kontext', 'UniPic2 Kontext', 'generation', 'python-ai-service', 'experimental', 'Advanced electric scene generation runtime', 'inspection robot, transformer yard, contextual electric environment', 'artifact, low detail, unrealistic scale', 'G:\\electric-ai-runtime\\models\\generation\\unipic2-kontext'),
('image-reward', 'ImageReward', 'scoring', 'python-ai-service', 'available', 'Text-image alignment scoring runtime', 'alignment scorer', '', 'G:\\electric-ai-runtime\\models\\scoring\\image-reward'),
('aesthetic-predictor', 'Aesthetic Predictor', 'scoring', 'python-ai-service', 'available', 'Aesthetic and composition scoring runtime', 'aesthetic scorer', '', 'G:\\electric-ai-runtime\\models\\scoring\\aesthetic-predictor')
ON DUPLICATE KEY UPDATE
display_name = VALUES(display_name),
model_type = VALUES(model_type),
service_name = VALUES(service_name),
status = VALUES(status),
description = VALUES(description),
default_positive_prompt = VALUES(default_positive_prompt),
default_negative_prompt = VALUES(default_negative_prompt),
local_path = VALUES(local_path);

INSERT INTO model_prompt_templates (template_name, scene_type, positive_prompt, negative_prompt)
VALUES
('Wind Farm Baseline', 'wind-farm', 'A modern wind turbine farm at sunset', 'blurry, deformed, low quality');
