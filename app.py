from flask import Flask, render_template, request, redirect, session, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import timedelta, datetime
import os, json
import gc

app = Flask(__name__)
app.secret_key = "silver_admin_secret_key_2026"
app.permanent_session_lifetime = timedelta(days=1)

# 1. Firebase 초기화 (Vercel 환경 변수 우선 지원)
if not firebase_admin._apps:
    try:
        # Vercel Settings에 등록할 'FIREBASE_JSON' 환경 변수를 확인
        firebase_info = os.environ.get("FIREBASE_JSON")
        
        if firebase_info:
            # 환경 변수가 있으면 그 내용을 딕셔너리로 변환해서 사용
            cred_dict = json.loads(firebase_info)
            cred = credentials.Certificate(cred_dict)
        else:
            # 환경 변수가 없으면 기존처럼 파일에서 읽음 (내 컴퓨터 작업용)
            cred = credentials.Certificate("firebase_key.json")
        
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"❌ 파이어베이스 초기화 실패: {e}")

db = firestore.client()
ADMIN_PASSWORD = "4357"

# 2. 메인 페이지
@app.route("/")
def index():
    try:
        # 최신글 30개 불러오기
        posts_ref = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING).limit(30)
        posts = []
        docs = posts_ref.get()
        
        for doc in docs:
            post = doc.to_dict()
            post["id"] = doc.id
            
            # 한국 시간 변환 (+9시간)
            if "created" in post and post["created"]:
                try:
                    kst_time = post["created"] + timedelta(hours=9)
                    post["time_display"] = kst_time.strftime('%Y-%m-%d %H:%M')
                except:
                    post["time_display"] = "시간 정보 없음"
            else:
                post["time_display"] = "방금 전"

            # 댓글 불러오기 (최신 20개)
            post["comments"] = []
            comments_docs = db.collection("posts").document(doc.id).collection("comments").order_by("created").limit(20).get()
            for c in comments_docs:
                c_data = c.to_dict()
                c_data["id"] = c.id
                post["comments"].append(c_data)
            posts.append(post)
        
        response = render_template("index.html", posts=posts)
        del posts
        gc.collect() 
        return response
    except Exception as e:
        gc.collect()
        return f"서버 연결 오류: {e}. 파이어베이스 설정을 확인해주세요."

# 3. 글쓰기 및 댓글 작성
@app.route("/submit", methods=["POST"])
def submit():
    content = request.form.get("content", "").strip()
    nickname = request.form.get("nickname", "익명").strip()
    if content:
        db.collection("posts").add({
            "nickname": nickname,
            "content": content,
            "reported": False,
            "created": firestore.SERVER_TIMESTAMP
        })
    gc.collect()
    return redirect("/")

@app.route("/comment/<post_id>", methods=["POST"])
def comment(post_id):
    content = request.form.get("content", "").strip()
    nickname = request.form.get("nickname", "익명").strip()
    if content:
        db.collection("posts").document(post_id).collection("comments").add({
            "nickname": nickname,
            "content": content,
            "reported": False,
            "created": firestore.SERVER_TIMESTAMP
        })
    gc.collect()
    return redirect("/")

# 4. 신고 및 관리자 기능
@app.route("/report/post/<post_id>", methods=["POST"])
def report_post(post_id):
    db.collection("posts").document(post_id).update({
        "reported": True,
        "report_reason": request.form.get("reason", "사유 없음")
    })
    return redirect("/")

@app.route("/silver_admin_hidden_2464", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        return "<script>alert('비밀번호가 틀렸습니다.'); history.back();</script>"
    
    if not session.get("admin"):
        return render_template("admin_login.html")
    
    docs = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING).limit(50).get()
    posts = []
    for doc in docs:
        post = doc.to_dict()
        post["id"] = doc.id
        posts.append(post)
    
    res = render_template("admin.html", posts=posts)
    gc.collect()
    return res

@app.route("/admin/delete/post/<post_id>", methods=["POST"])
def delete_post(post_id):
    if not session.get("admin"): return redirect("/")
    db.collection("posts").document(post_id).delete()
    return redirect(url_for("admin"))

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
