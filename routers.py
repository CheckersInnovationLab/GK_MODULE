import os
import json
import time
import random
import string
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from mysql.connector import Error

from app.schemas import (
    QuestionAddRequest, QuestionUpdateRequest, 
    AssessmentStartRequest, AssessmentEndRequest, 
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse,
    ProfileUpdate, ProfileResponse,
    UserAssessmentsSummaryResponse, QuestionListResponse, AssessmentResultsResponse
)
from app.database import get_db_connection

questions_router = APIRouter(
    prefix="/api/gk/questions",
    tags=["Questions"]
)

assessments_router = APIRouter(
    prefix="/api/gk/assessments",
    tags=["Assessments"]
)



categories_router = APIRouter(
    prefix="/api/gk/categories",
    tags=["Categories"]
)

profiles_router = APIRouter(
    prefix="/api/gk/profiles",
    tags=["Profiles"]
)

# --- Profiles ---
def _ensure_profile_exists(cursor, user_id: int):
    cursor.execute("SELECT gk_profile_id FROM xxed_gk_profiles_tab WHERE user_id = %s", (user_id,))
    if not cursor.fetchone():
        # Fetch from main app
        cursor.execute("SELECT first_name, last_name FROM xxed_user_profile_tab WHERE user_id = %s", (user_id,))
        ms_user = cursor.fetchone()
        if not ms_user:
            raise HTTPException(status_code=404, detail="User not found in Mindshaala system")
        first_name = ms_user.get('first_name') or ""
        last_name = ms_user.get('last_name') or ""
        user_name = f"{first_name} {last_name}".strip()
        
        cursor.execute(
            "INSERT INTO xxed_gk_profiles_tab (user_id, user_name, area_of_focus) VALUES (%s, %s, NULL)", 
            (user_id, user_name)
        )
        
        now = datetime.now()
        today = now.date()
        cursor.execute(
            "INSERT INTO xxed_gk_assessment_quotas_tab (user_id, start_quota_date, quota_date, used_count, max_limit, status) VALUES (%s, %s, %s, 0, 2, 1)",
            (user_id, now, today)
        )
        return True
    return False

@profiles_router.get("", response_model=ProfileResponse)
def get_profile(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if _ensure_profile_exists(cursor, user_id):
            conn.commit()
            
        cursor.execute("SELECT * FROM xxed_gk_profiles_tab WHERE user_id = %s", (user_id,))
        profile = cursor.fetchone()
        if not profile:
            raise HTTPException(status_code=404, detail="User profile does not exist.")
        if 'creation_date' in profile and profile['creation_date']:
            profile['creation_date'] = profile['creation_date'].isoformat()
            
        if profile.get('area_of_focus'):
            if isinstance(profile['area_of_focus'], str):
                try:
                    profile['area_of_focus'] = json.loads(profile['area_of_focus'])
                except json.JSONDecodeError:
                    profile['area_of_focus'] = []
                    
        profile['message'] = "Profile fetched successfully"
        return profile
    except HTTPException:
        raise
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@profiles_router.put("")
def update_profile(user_id: int, req: ProfileUpdate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        _ensure_profile_exists(cursor, user_id)
        
        area_of_focus_json = json.dumps([item.model_dump() for item in req.area_of_focus])
        
        cursor.execute("UPDATE xxed_gk_profiles_tab SET area_of_focus = %s WHERE user_id = %s", (area_of_focus_json, user_id))
        conn.commit()
        return {"message": "Profile updated successfully"}
    except HTTPException:
        raise
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# --- Categories ---
@categories_router.get("", response_model=CategoryListResponse)
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM xxed_gk_categories_tab")
        categories = cursor.fetchall()
        if not categories:
            return {"message": "No categories found", "data": []}
        return {"message": "Categories fetched successfully", "data": categories}
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@categories_router.post("", status_code=status.HTTP_201_CREATED)
def create_category(req: CategoryCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO xxed_gk_categories_tab (category_name, description, status) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (req.category_name, req.description, req.status))
        conn.commit()
        return {"message": "Category created successfully", "category_id": cursor.lastrowid}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@categories_router.put("")
def update_category(category_id: int, req: CategoryUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        updates = []
        params = []
        if req.category_name is not None:
            updates.append("category_name = %s")
            params.append(req.category_name)
        if req.description is not None:
            updates.append("description = %s")
            params.append(req.description)
        if req.status is not None:
            updates.append("status = %s")
            params.append(req.status)
            
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
            
        query = f"UPDATE xxed_gk_categories_tab SET {', '.join(updates)} WHERE category_id = %s"
        params.append(category_id)
        
        cursor.execute(query, tuple(params))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Category not found or no changes made")
            
        return {"message": "Category updated successfully"}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# --- Questions ---
@questions_router.get("/category", response_model=QuestionListResponse)
def get_questions_by_category(category_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM xxed_gk_questions_tab WHERE category_id = %s", (category_id,))
        questions = cursor.fetchall()
        if not questions:
            return {"message": "No questions found for this category", "data": []}
        return {"message": "Questions fetched successfully", "data": questions}
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@questions_router.post("", status_code=status.HTTP_201_CREATED)
def add_question(req: QuestionAddRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO xxed_gk_questions_tab 
            (category_id, location_id, event_year_month, gk_question, complexity, option_a, option_b, option_c, option_d, correct_answer, gk_answer, marks, status, creation_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, COALESCE(%s, CURRENT_TIMESTAMP(6)))
        """
        values = (req.category_id, req.location_id, req.event_year_month, req.gk_question, req.complexity, req.option_a, req.option_b, req.option_c, req.option_d, req.correct_answer, req.gk_answer, req.marks, req.creation_date)
        cursor.execute(query, values)
        new_id = cursor.lastrowid
        
        conn.commit()
        return {"message": "Question added successfully", "gk_question_id": new_id}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@questions_router.put("")
def update_question(gk_question_id: int, req: QuestionUpdateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        update_data = req.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")
            
        fields = []
        values = []
        for key, value in update_data.items():
            fields.append(f"{key} = %s")
            values.append(value)
            
        values.append(gk_question_id)
        query = f"UPDATE xxed_gk_questions_tab SET {', '.join(fields)} WHERE gk_question_id = %s"
        
        cursor.execute(query, tuple(values))
        
        if cursor.rowcount == 0:
            cursor.execute("SELECT gk_question_id FROM xxed_gk_questions_tab WHERE gk_question_id = %s", (gk_question_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Question not found")
        
        conn.commit()
        return {"message": "Question updated successfully"}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@questions_router.delete("")
def delete_question(gk_question_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM xxed_gk_questions_tab WHERE gk_question_id = %s", (gk_question_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Question not found")
        conn.commit()
        return {"message": "Question deleted successfully"}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# --- Assessments ---
@assessments_router.post("/start", status_code=status.HTTP_201_CREATED)
def create_assessment(req: AssessmentStartRequest):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 0. Profile Check (100% Complete)
        cursor.execute("SELECT area_of_focus FROM xxed_gk_profiles_tab WHERE user_id = %s", (req.user_id,))
        profile = cursor.fetchone()
        
        if not profile or profile['area_of_focus'] is None:
            raise HTTPException(status_code=400, detail="Please complete your GK profile first.")
            
        # 1. Quota Check
        today = datetime.now().date()
        cursor.execute("SELECT quota_id, start_quota_date, quota_date, used_count, max_limit, status FROM xxed_gk_assessment_quotas_tab WHERE user_id = %s", (req.user_id,))
        quota = cursor.fetchone()
        
        if not quota:
            now = datetime.now()
            cursor.execute("INSERT INTO xxed_gk_assessment_quotas_tab (user_id, start_quota_date, quota_date, used_count, max_limit, status) VALUES (%s, %s, %s, 0, 2, 1)", (req.user_id, now, today))
            used_count = 0
            max_limit = 2
        else:
            if quota['status'] == 0:
                raise HTTPException(status_code=403, detail="Assessments are disabled for this user.")
                
            quota_date = quota['quota_date']
            used_count = quota['used_count']
            max_limit = quota['max_limit']
            
            if quota_date < today:
                used_count = 0
                cursor.execute("UPDATE xxed_gk_assessment_quotas_tab SET used_count = 0, quota_date = %s WHERE user_id = %s", (today, req.user_id))
            
        if used_count >= max_limit:
            raise HTTPException(status_code=429, detail=f"Daily assessment quota reached. Maximum {max_limit} allowed.")

        # 2. Tier Selection
        total_questions = 40
        if req.assessment_type == "100M Advanced":
            total_questions = 100
            
        # 3. Mode Selection
        category_percentages = []
        if req.creation_mode == "Normal":
            area_of_focus = []
            if profile.get('area_of_focus'):
                if isinstance(profile['area_of_focus'], str):
                    try:
                        area_of_focus = json.loads(profile['area_of_focus'])
                    except json.JSONDecodeError:
                        area_of_focus = []
                else:
                    area_of_focus = profile['area_of_focus']
                    
            if not area_of_focus:
                 raise HTTPException(status_code=400, detail="Area of focus is not set in profile.")
            category_percentages = area_of_focus
            
        elif req.creation_mode == "Custom":
            if not req.category_ids:
                raise HTTPException(status_code=400, detail="category_ids must be provided for Custom mode.")
                
            format_strings = ','.join(['%s'] * len(req.category_ids))
            cursor.execute(f"SELECT category_id FROM xxed_gk_categories_tab WHERE category_id IN ({format_strings}) AND status = 1", tuple(req.category_ids))
            valid_categories = cursor.fetchall()
            valid_category_ids = [cat['category_id'] for cat in valid_categories]
            
            invalid_ids = [cid for cid in req.category_ids if cid not in valid_category_ids]
            if invalid_ids:
                count = len(invalid_ids)
                cat_word = "category is" if count == 1 else "categories are"
                raise HTTPException(status_code=400, detail=f"{count} selected {cat_word} invalid or currently inactive. Please refresh your selection.")
                
            equal_pct = 100.0 / len(req.category_ids)
            category_percentages = [{"category_id": cid, "percentage": equal_pct} for cid in req.category_ids]
        else:
            raise HTTPException(status_code=400, detail="Invalid creation_mode. Must be Normal or Custom.")

        # 4. Fetch Questions
        questions = []
        
        category_targets = []
        for cat in category_percentages:
            target = int(round((cat['percentage'] / 100.0) * total_questions))
            category_targets.append({
                "category_id": cat["category_id"],
                "target": target,
                "percentage": cat["percentage"]
            })
            
        current_target_total = sum(ct["target"] for ct in category_targets)
        if current_target_total != total_questions and category_targets:
            category_targets.sort(key=lambda x: x["percentage"], reverse=True)
            category_targets[0]["target"] += (total_questions - current_target_total)
            
        for ct in category_targets:
            if ct["target"] <= 0:
                continue
                
            query = """
                SELECT gk_question_id, gk_question, option_a, option_b, option_c, option_d, correct_answer 
                FROM xxed_gk_questions_tab 
                WHERE category_id = %s 
                ORDER BY RAND() LIMIT %s
            """
            cursor.execute(query, (ct["category_id"], ct["target"]))
            fetched = cursor.fetchall()
            
            if len(fetched) < ct["target"]:
                cursor.execute("SELECT category_name FROM xxed_gk_categories_tab WHERE category_id = %s", (ct["category_id"],))
                cat_row = cursor.fetchone()
                cat_name = cat_row['category_name'] if cat_row else f"ID {ct['category_id']}"
                raise HTTPException(status_code=400, detail=f"Insufficient questions for category '{cat_name}'. Needed {ct['target']}, but only found {len(fetched)}.")
                
            questions.extend(fetched)
            
        if not questions:
            raise HTTPException(status_code=400, detail="No questions available for the selected categories.")
            
        random.shuffle(questions)
            
        actual_total = len(questions)
        total_marks = actual_total * 1
        
        if req.assessment_type == "100M Advanced":
            total_time_seconds = 120 * 60
        else:
            total_time_seconds = 60 * 60
        
        # 5. Create Assessment Definition
        cursor.execute("SELECT MAX(gk_assessment_id) as last_id FROM xxed_gk_assessment_tab")
        last_id_row = cursor.fetchone()
        last_id = last_id_row['last_id'] if last_id_row and last_id_row['last_id'] else 0
        gk_assessment_name = f"GK-Exam-{last_id + 1}"
        
        insert_ass_query = """
            INSERT INTO xxed_gk_assessment_tab 
            (gk_assessment_name, assessment_type, creation_mode, gk_total_marks, gk_total_time, gk_total_question, gk_created_by, gk_status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
        """
        cursor.execute(insert_ass_query, (gk_assessment_name, req.assessment_type, req.creation_mode, total_marks, total_time_seconds, actual_total, req.user_id))
        gk_assessment_id = cursor.lastrowid
        
        # 6. Start User Assessment
        start_time = datetime.now()
        insert_user_ass_query = """
            INSERT INTO xxed_gk_user_assessment_tab 
            (user_id, gk_assessment_id, start_time, status) 
            VALUES (%s, %s, %s, 'in-progress')
        """
        cursor.execute(insert_user_ass_query, (req.user_id, gk_assessment_id, start_time))
        gk_user_ass_id = cursor.lastrowid
        
        # 7. Pre-fill questions in User Answers Table
        insert_answers_query = """
            INSERT INTO xxed_gk_user_answers_tab 
            (gk_user_ass_id, gk_question_id, correct_answer, status, time_taken_seconds) 
            VALUES (%s, %s, %s, 'pending', 0)
        """
        answers_data = []
        clean_questions = []
        for q in questions:
            answers_data.append((gk_user_ass_id, q['gk_question_id'], q['correct_answer']))
            # Remove correct_answer from the response sent to frontend
            q_clean = {k: v for k, v in q.items() if k != 'correct_answer'}
            clean_questions.append(q_clean)
            
        cursor.executemany(insert_answers_query, answers_data)
        
        # 8. Increment Quota
        cursor.execute("UPDATE xxed_gk_assessment_quotas_tab SET used_count = used_count + 1 WHERE user_id = %s", (req.user_id,))
        
        conn.commit()
        
        return {
            "message": "Assessment started", 
            "gk_user_ass_id": gk_user_ass_id,
            "gk_assessment_id": gk_assessment_id,
            "gk_assessment_name": gk_assessment_name,
            "total_marks": total_marks,
            "total_time_seconds": total_time_seconds,
            "start_time": start_time,
            "questions": clean_questions
        }
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@assessments_router.post("/end")
def end_assessment(gk_user_ass_id: int, req: AssessmentEndRequest):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM xxed_gk_user_assessment_tab WHERE gk_user_ass_id = %s", (gk_user_ass_id,))
        user_assessment = cursor.fetchone()
        if not user_assessment:
            raise HTTPException(status_code=404, detail="User Assessment not found")
        
        total_score = 0
        correct_count = 0
        incorrect_count = 0
        skipped_count = 0
        
        update_answer_query = """
            UPDATE xxed_gk_user_answers_tab 
            SET user_answer = %s, status = %s, time_taken_seconds = %s
            WHERE gk_user_ass_id = %s AND gk_question_id = %s
        """
        
        for ans in req.answers:
            cursor.execute("SELECT correct_answer, marks FROM xxed_gk_questions_tab WHERE gk_question_id = %s", (ans.gk_question_id,))
            q_data = cursor.fetchone()
            
            if not q_data:
                continue
            
            correct_ans = q_data['correct_answer']
            marks = q_data['marks']
            
            status_val = 'skipped'
            if ans.user_answer is not None and ans.user_answer.strip() != "":
                if ans.user_answer.upper() == correct_ans.upper():
                    status_val = 'correct'
                    correct_count += 1
                    total_score += marks
                else:
                    status_val = 'incorrect'
                    incorrect_count += 1
            else:
                skipped_count += 1
                
            cursor.execute(update_answer_query, (
                ans.user_answer,
                status_val, 
                ans.time_taken_seconds,
                gk_user_ass_id, 
                ans.gk_question_id
            ))
            
        # 2. Mark any unanswered questions that were left as 'pending' to 'skipped'
        cursor.execute("UPDATE xxed_gk_user_answers_tab SET status = 'skipped' WHERE gk_user_ass_id = %s AND status = 'pending'", (gk_user_ass_id,))
        
        # 3. Calculate Final Results securely from the database
        cursor.execute("""
            SELECT 
                COUNT(*) as total_questions,
                SUM(CASE WHEN status = 'correct' THEN 1 ELSE 0 END) as correct_count,
                SUM(CASE WHEN status = 'incorrect' THEN 1 ELSE 0 END) as incorrect_count,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_count
            FROM xxed_gk_user_answers_tab 
            WHERE gk_user_ass_id = %s
        """, (gk_user_ass_id,))
        stats = cursor.fetchone()
        
        cursor.execute("""
            SELECT SUM(q.marks) as total_score
            FROM xxed_gk_user_answers_tab a
            JOIN xxed_gk_questions_tab q ON a.gk_question_id = q.gk_question_id
            WHERE a.gk_user_ass_id = %s AND a.status = 'correct'
        """, (gk_user_ass_id,))
        score_row = cursor.fetchone()
        
        total_score = int(score_row['total_score']) if score_row and score_row['total_score'] else 0
        correct_count = int(stats['correct_count']) if stats['correct_count'] else 0
        incorrect_count = int(stats['incorrect_count']) if stats['incorrect_count'] else 0
        skipped_count = int(stats['skipped_count']) if stats['skipped_count'] else 0
        total_questions = int(stats['total_questions']) if stats['total_questions'] else 0
        
        accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0.0
        end_time = datetime.now()
        
        update_assessment_query = """
            UPDATE xxed_gk_user_assessment_tab 
            SET end_time = %s, total_score = %s, correct_count = %s, 
                incorrect_count = %s, skipped_count = %s, accuracy = %s, status = 'completed'
            WHERE gk_user_ass_id = %s
        """
        cursor.execute(update_assessment_query, (
            end_time, total_score, correct_count, incorrect_count, skipped_count, accuracy, gk_user_ass_id
        ))
        
        conn.commit()
        return {
            "message": "Assessment ended successfully",
            "total_score": total_score,
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "skipped_count": skipped_count,
            "accuracy": float(f"{accuracy:.2f}")
        }
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@assessments_router.get("/user", response_model=UserAssessmentsSummaryResponse)
def get_user_assessments(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT ua.gk_user_ass_id, a.gk_assessment_id, a.gk_assessment_name,
                   a.assessment_type, a.creation_mode,
                   ua.start_time, ua.end_time, ua.total_score, ua.correct_count, 
                   ua.incorrect_count, ua.skipped_count, ua.accuracy, ua.status
            FROM xxed_gk_user_assessment_tab ua
            JOIN xxed_gk_assessment_tab a ON ua.gk_assessment_id = a.gk_assessment_id
            WHERE ua.user_id = %s
            ORDER BY ua.start_time DESC
        """, (user_id,))
        assessments = cursor.fetchall()
        
        for ass in assessments:
            if ass['start_time']:
                ass['start_time'] = ass['start_time'].isoformat()
            if ass['end_time']:
                ass['end_time'] = ass['end_time'].isoformat()
                
        if not assessments:
            return {
                "message": "No assessments taken yet",
                "total_assessments": 0,
                "assessments": []
            }
                
        return {
            "message": "Assessments fetched successfully",
            "total_assessments": len(assessments),
            "assessments": assessments
        }
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@assessments_router.get("/results", response_model=AssessmentResultsResponse, responses={
    200: {
        "description": "Assessment Results Details",
        "content": {
            "application/json": {
                "example": {
                    "message": "Results fetched successfully",
                    "assessment_summary": {
                        "gk_user_ass_id": 1,
                        "user_id": 101,
                        "gk_assessment_id": 1,
                        "gk_assessment_name": "GK-Exam-1",
                        "gk_total_marks": 40,
                        "total_score": 15,
                        "accuracy": 37.5,
                        "status": "completed"
                    },
                    "details": [
                        {
                            "gk_question_id": 5,
                            "gk_question": "What is the capital of France?",
                            "option_a": "Berlin",
                            "option_b": "Paris",
                            "option_c": "Madrid",
                            "option_d": "Rome",
                            "correct_answer": "B",
                            "gk_answer": "Paris is the capital and most populous city of France.",
                            "user_answer": "B",
                            "status": "correct",
                            "time_taken_seconds": 12
                        }
                    ]
                }
            }
        }
    }
})
def get_assessment_results(gk_user_ass_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT ua.*, a.gk_assessment_name, a.assessment_type, a.creation_mode, a.gk_total_marks, a.gk_total_time 
            FROM xxed_gk_user_assessment_tab ua
            JOIN xxed_gk_assessment_tab a ON ua.gk_assessment_id = a.gk_assessment_id
            WHERE ua.gk_user_ass_id = %s
        """, (gk_user_ass_id,))
        assessment = cursor.fetchone()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment results not found.")
            
        cursor.execute("""
            SELECT u.gk_question_id, q.gk_question, q.option_a, q.option_b, q.option_c, q.option_d,
                   q.correct_answer, q.gk_answer, q.marks,
                   u.user_answer, u.status, u.time_taken_seconds
            FROM xxed_gk_user_answers_tab u
            JOIN xxed_gk_questions_tab q ON u.gk_question_id = q.gk_question_id
            WHERE u.gk_user_ass_id = %s
        """, (gk_user_ass_id,))
        answers = cursor.fetchall()
        
        return {
            "message": "Results fetched successfully",
            "assessment_summary": assessment,
            "details": answers
        }
    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@assessments_router.delete("/user-assessment")
def delete_user_assessment(gk_user_ass_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if exists
        cursor.execute("SELECT * FROM xxed_gk_user_assessment_tab WHERE gk_user_ass_id = %s", (gk_user_ass_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User Assessment not found.")
            
        # Manage foreign key constraints explicitly: delete child records first
        cursor.execute("DELETE FROM xxed_gk_user_answers_tab WHERE gk_user_ass_id = %s", (gk_user_ass_id,))
        
        # Delete user assessment
        cursor.execute("DELETE FROM xxed_gk_user_assessment_tab WHERE gk_user_ass_id = %s", (gk_user_ass_id,))
        
        conn.commit()
        return {"message": "User Assessment and related answers deleted successfully."}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@assessments_router.delete("/assessment")
def delete_assessment(gk_assessment_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if exists
        cursor.execute("SELECT * FROM xxed_gk_assessment_tab WHERE gk_assessment_id = %s", (gk_assessment_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Assessment not found.")
            
        # Manage foreign key constraints explicitly: find all related user assessments
        cursor.execute("SELECT gk_user_ass_id FROM xxed_gk_user_assessment_tab WHERE gk_assessment_id = %s", (gk_assessment_id,))
        user_assessments = cursor.fetchall()
        
        # Delete all related answers for each user assessment
        for ua in user_assessments:
            cursor.execute("DELETE FROM xxed_gk_user_answers_tab WHERE gk_user_ass_id = %s", (ua['gk_user_ass_id'],))
            
        # Delete all user assessments for this assessment
        cursor.execute("DELETE FROM xxed_gk_user_assessment_tab WHERE gk_assessment_id = %s", (gk_assessment_id,))
        
        # Delete the main assessment
        cursor.execute("DELETE FROM xxed_gk_assessment_tab WHERE gk_assessment_id = %s", (gk_assessment_id,))
        
        conn.commit()
        return {"message": "Assessment and all related user assessments/answers deleted successfully."}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
