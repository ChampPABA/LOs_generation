-- Initialize database with seed data

-- Insert Bloom's Taxonomy levels
INSERT INTO bloom_levels (level, name, description, keywords) VALUES
(1, 'Remember', 'Retrieve relevant knowledge from long-term memory', 'define, duplicate, list, memorize, recall, repeat, reproduce, state'),
(2, 'Understand', 'Construct meaning from instructional messages', 'classify, describe, discuss, explain, identify, locate, recognize, report, select, translate'),
(3, 'Apply', 'Carry out or use a procedure in a given situation', 'execute, implement, solve, use, demonstrate, interpret, operate, schedule, sketch'),
(4, 'Analyze', 'Break material into constituent parts and determine relationships', 'differentiate, organize, relate, compare, contrast, distinguish, examine, experiment, question, test'),
(5, 'Evaluate', 'Make judgments based on criteria and standards', 'appraise, argue, defend, judge, select, support, value, critique, weigh'),
(6, 'Create', 'Put elements together to form a coherent whole', 'design, assemble, construct, conjecture, develop, formulate, author, investigate');

-- Insert exam types
INSERT INTO exam_types (name, display_name, description, country_code, language_code, has_published_los, requires_generation) VALUES
('TBAT', 'Thai Basic Aptitude Test', 'Thai university entrance exam focusing on basic academic aptitude', 'TH', 'th', false, true),
('PMAT', 'Professional and Academic Aptitude Test', 'Thai professional and academic aptitude assessment', 'TH', 'th', false, true),
('GAT', 'General Aptitude Test', 'General aptitude test for Thai students', 'TH', 'th', false, true),
('PAT', 'Professional Aptitude Test', 'Professional aptitude test for specific fields', 'TH', 'th', false, true);

-- Insert subjects for TBAT
INSERT INTO subjects (exam_type_id, name, display_name, description, code, is_active) VALUES
((SELECT id FROM exam_types WHERE name = 'TBAT'), 'physics', 'Physics', 'Physics concepts and principles', 'PHY', true),
((SELECT id FROM exam_types WHERE name = 'TBAT'), 'chemistry', 'Chemistry', 'Chemistry concepts and principles', 'CHE', true),
((SELECT id FROM exam_types WHERE name = 'TBAT'), 'biology', 'Biology', 'Biology concepts and principles', 'BIO', true);

-- Insert Physics topics for TBAT
INSERT INTO topics (subject_id, name, description, blueprint_text, topic_order, is_active) VALUES
((SELECT id FROM subjects WHERE name = 'physics' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Kinematics and Forces', 'Motion and forces acting on objects', 'Motion in one and two dimensions, Newton''s laws of motion, friction, circular motion', 1, true),
((SELECT id FROM subjects WHERE name = 'physics' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Energy and Momentum', 'Conservation laws and energy transformations', 'Work and energy, conservation of energy, momentum and collisions', 2, true),
((SELECT id FROM subjects WHERE name = 'physics' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Waves and Sound', 'Wave phenomena and sound properties', 'Wave properties, sound waves, interference, diffraction', 3, true),
((SELECT id FROM subjects WHERE name = 'physics' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Electricity and Magnetism', 'Electric and magnetic phenomena', 'Electric fields, circuits, magnetic fields, electromagnetic induction', 4, true),
((SELECT id FROM subjects WHERE name = 'physics' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Thermodynamics', 'Heat and temperature concepts', 'Temperature, heat transfer, laws of thermodynamics, kinetic theory', 5, true),
((SELECT id FROM subjects WHERE name = 'physics' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Optics', 'Light and optical phenomena', 'Reflection, refraction, lenses, mirrors, optical instruments', 6, true),
((SELECT id FROM subjects WHERE name = 'physics' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Modern Physics', 'Quantum mechanics and relativity', 'Atomic structure, radioactivity, nuclear physics, special relativity', 7, true);

-- Insert Chemistry topics for TBAT
INSERT INTO topics (subject_id, name, description, blueprint_text, topic_order, is_active) VALUES
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Atomic Structure', 'Structure and properties of atoms', 'Electron configuration, periodic trends, atomic models', 1, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Chemical Bonding', 'Types of chemical bonds and molecular structure', 'Ionic, covalent, metallic bonding, VSEPR theory, hybridization', 2, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'States of Matter', 'Properties of gases, liquids, and solids', 'Gas laws, intermolecular forces, phase changes', 3, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Solutions', 'Properties and behavior of solutions', 'Concentration, colligative properties, solubility', 4, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Chemical Reactions', 'Types and mechanisms of chemical reactions', 'Reaction types, stoichiometry, limiting reagents', 5, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Thermochemistry', 'Energy changes in chemical reactions', 'Enthalpy, entropy, Gibbs free energy, calorimetry', 6, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Chemical Kinetics', 'Rates and mechanisms of chemical reactions', 'Reaction rates, rate laws, activation energy, catalysis', 7, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Chemical Equilibrium', 'Equilibrium in chemical systems', 'Le Chatelier''s principle, equilibrium constants, acid-base equilibria', 8, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Acids and Bases', 'Properties and reactions of acids and bases', 'pH, titrations, buffer systems, acid-base theories', 9, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Electrochemistry', 'Chemical reactions involving electricity', 'Redox reactions, electrochemical cells, electrolysis', 10, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Organic Chemistry Basics', 'Introduction to organic compounds', 'Hydrocarbons, functional groups, nomenclature, isomerism', 11, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Nuclear Chemistry', 'Nuclear reactions and radioactivity', 'Radioactive decay, nuclear equations, half-life', 12, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Environmental Chemistry', 'Chemistry of environmental processes', 'Air and water pollution, green chemistry principles', 13, true),
((SELECT id FROM subjects WHERE name = 'chemistry' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Analytical Chemistry', 'Methods for chemical analysis', 'Qualitative and quantitative analysis, spectroscopy basics', 14, true);

-- Insert Biology topics for TBAT
INSERT INTO topics (subject_id, name, description, blueprint_text, topic_order, is_active) VALUES
((SELECT id FROM subjects WHERE name = 'biology' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Cell Biology', 'Structure and function of cells', 'Cell theory, organelles, cell membrane, cellular processes', 1, true),
((SELECT id FROM subjects WHERE name = 'biology' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Genetics', 'Inheritance and genetic principles', 'Mendelian genetics, DNA structure, gene expression, mutations', 2, true),
((SELECT id FROM subjects WHERE name = 'biology' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Evolution', 'Evolutionary processes and evidence', 'Natural selection, speciation, phylogeny, evidence for evolution', 3, true),
((SELECT id FROM subjects WHERE name = 'biology' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Ecology', 'Interactions between organisms and environment', 'Ecosystems, population dynamics, biodiversity, conservation', 4, true),
((SELECT id FROM subjects WHERE name = 'biology' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Human Physiology', 'Structure and function of human body systems', 'Circulatory, respiratory, digestive, nervous systems', 5, true),
((SELECT id FROM subjects WHERE name = 'biology' AND exam_type_id = (SELECT id FROM exam_types WHERE name = 'TBAT')), 
 'Molecular Biology', 'Molecular mechanisms of life', 'Protein synthesis, enzyme function, metabolic pathways', 6, true);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_subjects_exam_type ON subjects(exam_type_id);
CREATE INDEX IF NOT EXISTS idx_topics_subject ON topics(subject_id);
CREATE INDEX IF NOT EXISTS idx_topics_order ON topics(subject_id, topic_order);

-- Grant necessary permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO los_user;