"""
Test data fixtures and sample data for testing.
"""

from typing import Dict, List, Any
import json
from datetime import datetime, timedelta


# Sample Physics Content
SAMPLE_PHYSICS_CONTENT = """
Force and Motion

Force is a push or pull that can change the motion of an object. When you push a door open or pull a rope, you are applying a force. Forces can cause objects to start moving, stop moving, speed up, slow down, or change direction.

Newton's Laws of Motion

Sir Isaac Newton developed three important laws that describe how forces affect motion:

1. First Law (Law of Inertia): An object at rest stays at rest, and an object in motion stays in motion at constant velocity, unless acted upon by an unbalanced force.

2. Second Law: The acceleration of an object is directly proportional to the net force acting on it and inversely proportional to its mass. This is expressed as F = ma, where F is force, m is mass, and a is acceleration.

3. Third Law: For every action, there is an equal and opposite reaction.

Types of Forces

There are several types of forces:
- Gravitational force: The force of attraction between objects with mass
- Friction force: The force that opposes motion between surfaces in contact
- Normal force: The force perpendicular to a surface
- Applied force: A force that is applied to an object by a person or another object
- Tension force: The force transmitted through a string, rope, cable, or wire

Examples and Applications

Understanding forces helps us explain many everyday phenomena:
- Why we need to wear seatbelts in cars (inertia)
- How rockets work (Newton's third law)
- Why it's harder to stop a heavy truck than a light car (Newton's second law)
- Why objects fall to the ground (gravitational force)
"""

# Sample Thai Physics Content
SAMPLE_THAI_CONTENT = """
แรงและการเคลื่อนที่

แรงคือการผลักหรือดึงที่สามารถเปลี่ยนการเคลื่อนที่ของวัตถุได้ เมื่อคุณผลักประตูให้เปิดหรือดึงเชือก คุณกำลังใช้แรง แรงสามารถทำให้วัตถุเริ่มเคลื่อนที่ หยุดเคลื่อนที่ เร่งความเร็ว ลดความเร็ว หรือเปลี่ยนทิศทาง

กฎการเคลื่อนที่ของนิวตัน

เซอร์ไอแซก นิวตัน ได้พัฒนากฎสำคัญสามข้อที่อธิบายว่าแรงส่งผลต่อการเคลื่อนที่อย่างไร:

1. กฎข้อที่หนึ่ง (กฎความเฉื่อย): วัตถุที่อยู่นิ่งจะอยู่นิ่งต่อไป และวัตถุที่เคลื่อนที่จะเคลื่อนที่ต่อไปด้วยความเร็วคงที่ เว้นแต่จะมีแรงที่ไม่สมดุลมากระทำ

2. กฎข้อที่สอง: ความเร่งของวัตถุเป็นสัดส่วนโดยตรงกับแรงลัพธ์ที่กระทำต่อวัตถุ และเป็นสัดส่วนผกผันกับมวลของวัตถุ แสดงเป็น F = ma โดยที่ F คือแรง m คือมวล และ a คือความเร่ง

3. กฎข้อที่สาม: การกระทำทุกครั้งจะมีปฏิกิริยาที่เท่ากันและตรงข้าม
"""

# Sample Learning Objectives
SAMPLE_LEARNING_OBJECTIVES = [
    {
        "objective_text": "Students will be able to define force as a push or pull that can change the motion of objects",
        "bloom_level": "remember",
        "action_verbs": ["define", "identify"],
        "difficulty": "beginner",
        "assessment_suggestions": ["multiple choice", "definition matching"],
        "quality_scores": {
            "clarity_score": 0.9,
            "relevance_score": 0.85,
            "measurability_score": 0.8,
            "overall_score": 0.85
        }
    },
    {
        "objective_text": "Students will be able to calculate the force required to accelerate an object using F = ma",
        "bloom_level": "apply",
        "action_verbs": ["calculate", "solve", "compute"],
        "difficulty": "intermediate",
        "assessment_suggestions": ["problem solving", "calculation exercises"],
        "quality_scores": {
            "clarity_score": 0.95,
            "relevance_score": 0.9,
            "measurability_score": 0.95,
            "overall_score": 0.93
        }
    },
    {
        "objective_text": "Students will be able to analyze the relationship between force, mass, and acceleration in real-world scenarios",
        "bloom_level": "analyze",
        "action_verbs": ["analyze", "examine", "investigate"],
        "difficulty": "advanced",
        "assessment_suggestions": ["case study analysis", "experimental design"],
        "quality_scores": {
            "clarity_score": 0.85,
            "relevance_score": 0.9,
            "measurability_score": 0.8,
            "overall_score": 0.85
        }
    },
    {
        "objective_text": "Students will be able to evaluate the effectiveness of different types of forces in various applications",
        "bloom_level": "evaluate",
        "action_verbs": ["evaluate", "assess", "critique"],
        "difficulty": "advanced",
        "assessment_suggestions": ["project evaluation", "peer review"],
        "quality_scores": {
            "clarity_score": 0.8,
            "relevance_score": 0.85,
            "measurability_score": 0.75,
            "overall_score": 0.8
        }
    },
    {
        "objective_text": "Students will be able to create experiments to demonstrate Newton's laws of motion",
        "bloom_level": "create",
        "action_verbs": ["create", "design", "develop"],
        "difficulty": "advanced",
        "assessment_suggestions": ["laboratory work", "project creation"],
        "quality_scores": {
            "clarity_score": 0.9,
            "relevance_score": 0.95,
            "measurability_score": 0.85,
            "overall_score": 0.9
        }
    }
]

# Sample Chunks Data
SAMPLE_CHUNKS = [
    {
        "chunk_id": "chunk-001",
        "content": "Force is a push or pull that can change the motion of an object. When you push a door open or pull a rope, you are applying a force.",
        "quality_score": 0.85,
        "metadata": {
            "source_document": "physics_textbook.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "language_code": "en",
            "language_confidence": 0.95,
            "char_count": 124,
            "word_count": 23
        }
    },
    {
        "chunk_id": "chunk-002",
        "content": "Newton's First Law (Law of Inertia): An object at rest stays at rest, and an object in motion stays in motion at constant velocity, unless acted upon by an unbalanced force.",
        "quality_score": 0.92,
        "metadata": {
            "source_document": "physics_textbook.pdf",
            "page_number": 1,
            "chunk_index": 1,
            "language_code": "en",
            "language_confidence": 0.98,
            "char_count": 166,
            "word_count": 28
        }
    },
    {
        "chunk_id": "chunk-003",
        "content": "Newton's Second Law: The acceleration of an object is directly proportional to the net force acting on it and inversely proportional to its mass. F = ma.",
        "quality_score": 0.88,
        "metadata": {
            "source_document": "physics_textbook.pdf",
            "page_number": 1,
            "chunk_index": 2,
            "language_code": "en",
            "language_confidence": 0.96,
            "char_count": 146,
            "word_count": 24
        }
    }
]

# Sample Vector Search Results
SAMPLE_VECTOR_RESULTS = [
    {
        "id": "chunk-001",
        "score": 0.95,
        "text": "Force is a push or pull that can change the motion of an object.",
        "language": "en",
        "metadata": {
            "source": "physics_textbook.pdf",
            "page": 1,
            "topic": "forces"
        }
    },
    {
        "id": "chunk-004",
        "score": 0.87,
        "text": "Gravitational force is the force of attraction between objects with mass.",
        "language": "en",
        "metadata": {
            "source": "physics_textbook.pdf",
            "page": 2,
            "topic": "gravity"
        }
    },
    {
        "id": "chunk-007",
        "score": 0.82,
        "text": "Friction force opposes motion between surfaces in contact.",
        "language": "en",
        "metadata": {
            "source": "physics_textbook.pdf",
            "page": 3,
            "topic": "friction"
        }
    }
]

# Sample API Responses
SAMPLE_API_RESPONSES = {
    "health_check": {
        "status": "healthy",
        "timestamp": "2025-01-27T10:30:00Z",
        "uptime_seconds": 3600,
        "services": {
            "database": "healthy",
            "redis": "healthy",
            "qdrant": "healthy",
            "llm_service": "healthy"
        }
    },
    "generation_job_created": {
        "job_id": "job-12345",
        "status": "queued",
        "message": "Learning objectives generation job created successfully",
        "estimated_completion": "2025-01-27T10:35:00Z"
    },
    "generation_completed": {
        "job_id": "job-12345",
        "status": "completed",
        "topic": "Forces and Motion",
        "generation_successful": True,
        "requested_count": 5,
        "generated_count": 5,
        "validated_count": 4,
        "objectives": SAMPLE_LEARNING_OBJECTIVES,
        "generation_stats": {
            "avg_quality_score": 0.866,
            "processing_time_seconds": 12.5,
            "context_chunks_used": 8,
            "avg_relevance_score": 0.89
        }
    }
}

# Sample Configuration Data
SAMPLE_CONFIGURATIONS = {
    "development": {
        "environment": "development",
        "debug": True,
        "force_https": False,
        "api_rate_limit_per_minute": 200,
        "api_rate_limit_per_hour": 5000,
        "database_pool_size": 10,
        "max_concurrent_jobs": 5,
        "log_level": "DEBUG",
        "cors_origins": ["http://localhost:3000"],
        "chunk_size": 1000,
        "overlap_size": 200
    },
    "production": {
        "environment": "production",
        "debug": False,
        "force_https": True,
        "api_rate_limit_per_minute": 60,
        "api_rate_limit_per_hour": 1000,
        "database_pool_size": 20,
        "max_concurrent_jobs": 10,
        "log_level": "WARNING",
        "cors_origins": ["https://app.yourdomain.com"],
        "chunk_size": 1000,
        "overlap_size": 200
    }
}

# Test Database Data
TEST_DATABASE_RECORDS = {
    "textbooks": [
        {
            "id": 1,
            "title": "Introduction to Physics",
            "subject": "Physics",
            "grade_level": "Grade 10",
            "publisher": "Education Press",
            "isbn": "978-0123456789",
            "file_path": "/data/textbooks/intro_physics.pdf",
            "file_size_bytes": 2048576,
            "total_pages": 120,
            "file_hash": "abc123def456",
            "processing_status": "completed",
            "language_detected": "en"
        },
        {
            "id": 2,
            "title": "ฟิสิกส์พื้นฐาน",
            "subject": "Physics",
            "grade_level": "มัธยมศึกษาปีที่ 4",
            "publisher": "สำนักพิมพ์การศึกษา",
            "isbn": "978-6161234567",
            "file_path": "/data/textbooks/thai_physics.pdf",
            "file_size_bytes": 3145728,
            "total_pages": 150,
            "file_hash": "def789ghi012",
            "processing_status": "processing",
            "language_detected": "th"
        }
    ],
    "learning_objectives": [
        {
            "id": 1,
            "objective_text": "Students will be able to define force as a push or pull",
            "bloom_level_id": 1,
            "topic_id": 1,
            "source_textbook_id": 1,
            "parent_chunk_ids": [1, 2],
            "relevance_score": 0.85,
            "clarity_score": 0.9,
            "coverage_score": 0.8,
            "overall_quality_score": 0.85,
            "validation_status": "approved",
            "created_at": datetime.now() - timedelta(days=1)
        }
    ],
    "topics": [
        {
            "id": 1,
            "name": "Forces and Motion",
            "description": "Basic concepts of forces and their effects on motion",
            "subject_area": "Physics",
            "grade_level": "Grade 10"
        },
        {
            "id": 2,
            "name": "Energy Conservation",
            "description": "Principles of energy conservation and transformation",
            "subject_area": "Physics",
            "grade_level": "Grade 10"
        }
    ],
    "bloom_levels": [
        {"id": 1, "level_name": "Remember", "level_number": 1, "description": "Recall information"},
        {"id": 2, "level_name": "Understand", "level_number": 2, "description": "Comprehend meaning"},
        {"id": 3, "level_name": "Apply", "level_number": 3, "description": "Use knowledge"},
        {"id": 4, "level_name": "Analyze", "level_number": 4, "description": "Break down information"},
        {"id": 5, "level_name": "Evaluate", "level_number": 5, "description": "Make judgments"},
        {"id": 6, "level_name": "Create", "level_number": 6, "description": "Produce new content"}
    ]
}

# Performance Test Data
PERFORMANCE_TEST_DATA = {
    "large_content": "This is test content for performance testing. " * 1000,
    "multiple_topics": [
        "Forces and Motion", "Energy Conservation", "Wave Properties",
        "Electric Circuits", "Thermodynamics", "Optics", "Magnetism",
        "Atomic Structure", "Radioactivity", "Modern Physics"
    ],
    "stress_test_requests": 100,
    "concurrent_users": 20,
    "load_duration_seconds": 30
}

# Error Test Cases
ERROR_TEST_CASES = {
    "invalid_topic": {
        "topic": "",  # Empty topic
        "expected_error": "Topic cannot be empty"
    },
    "invalid_content_length": {
        "content": "short",  # Too short
        "expected_error": "Content must be at least 50 characters"
    },
    "invalid_count": {
        "count": 0,  # Invalid count
        "expected_error": "Count must be between 1 and 20"
    },
    "malformed_request": {
        "invalid_field": "value",
        "expected_error": "Invalid request format"
    }
}


def get_sample_data(data_type: str) -> Any:
    """Get sample data by type."""
    data_map = {
        "physics_content": SAMPLE_PHYSICS_CONTENT,
        "thai_content": SAMPLE_THAI_CONTENT,
        "learning_objectives": SAMPLE_LEARNING_OBJECTIVES,
        "chunks": SAMPLE_CHUNKS,
        "vector_results": SAMPLE_VECTOR_RESULTS,
        "api_responses": SAMPLE_API_RESPONSES,
        "configurations": SAMPLE_CONFIGURATIONS,
        "database_records": TEST_DATABASE_RECORDS,
        "performance_data": PERFORMANCE_TEST_DATA,
        "error_cases": ERROR_TEST_CASES
    }
    
    return data_map.get(data_type)


def create_test_chunks(count: int = 10, content_template: str = None) -> List[Dict[str, Any]]:
    """Create test chunks for testing."""
    if content_template is None:
        content_template = "This is test chunk content number {index} about physics concepts."
    
    chunks = []
    for i in range(count):
        chunk = {
            "chunk_id": f"test-chunk-{i:03d}",
            "content": content_template.format(index=i),
            "quality_score": 0.7 + (i % 3) * 0.1,  # Vary quality scores
            "metadata": {
                "source_document": f"test_doc_{i // 5}.pdf",
                "chunk_index": i,
                "language_code": "en",
                "language_confidence": 0.9 + (i % 10) * 0.01
            }
        }
        chunks.append(chunk)
    
    return chunks


def create_test_objectives(count: int = 5, topic: str = "Test Topic") -> List[Dict[str, Any]]:
    """Create test learning objectives."""
    bloom_levels = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
    difficulties = ["beginner", "intermediate", "advanced"]
    
    objectives = []
    for i in range(count):
        bloom_level = bloom_levels[i % len(bloom_levels)]
        difficulty = difficulties[i % len(difficulties)]
        
        objective = {
            "objective_text": f"Students will be able to {bloom_level.lower()} concepts related to {topic} (objective {i+1})",
            "bloom_level": bloom_level,
            "action_verbs": [bloom_level.lower()],
            "difficulty": difficulty,
            "assessment_suggestions": ["test", "assignment"],
            "quality_scores": {
                "clarity_score": 0.8 + (i % 5) * 0.04,
                "relevance_score": 0.75 + (i % 4) * 0.05,
                "measurability_score": 0.7 + (i % 6) * 0.05,
                "overall_score": 0.75 + (i % 5) * 0.05
            }
        }
        objectives.append(objective)
    
    return objectives
