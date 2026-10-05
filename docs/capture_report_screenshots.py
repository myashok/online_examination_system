from pathlib import Path
import sys
from uuid import uuid4

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:8080"
OUTPUT = Path(__file__).resolve().parent / "report-assets" / "current"
VIEWPORT = {"width": 1440, "height": 900}


def capture(page, name):
    page.wait_for_load_state("networkidle")
    page.screenshot(path=OUTPUT / f"{name}.png", full_page=False)


def login(page, email, password):
    page.goto(f"{BASE_URL}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_load_state("networkidle")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        if "--admin-only" in sys.argv:
            admin = browser.new_page(viewport=VIEWPORT)
            login(admin, "admin@oes.local", "Admin@12345")
            capture(admin, "admin-summary")
            admin.get_by_role("table").scroll_into_view_if_needed()
            capture(admin, "admin-summary-detail")
            admin.goto(f"{BASE_URL}/admin/users")
            capture(admin, "admin-users")
            admin.goto(f"{BASE_URL}/admin/audit")
            capture(admin, "admin-audit")
            browser.close()
            return
        if "--reports-only" in sys.argv:
            faculty = browser.new_page(viewport=VIEWPORT)
            login(faculty, "faculty@oes.local", "Faculty@12345")
            faculty.goto(f"{BASE_URL}/faculty/reports/1")
            faculty.get_by_role("heading", name="Operating Systems Midterm").wait_for()
            capture(faculty, "faculty-report")
            faculty.get_by_role("heading", name="Topic and difficulty").scroll_into_view_if_needed()
            capture(faculty, "faculty-analytics")
            browser.close()
            return
        if "--evaluation-only" in sys.argv:
            faculty = browser.new_page(viewport=VIEWPORT)
            login(faculty, "faculty@oes.local", "Faculty@12345")
            faculty.goto(f"{BASE_URL}/faculty/evaluation")
            item = faculty.locator("aside button.ghost").first
            item.wait_for()
            item.click()
            faculty.get_by_role("button", name="Save descriptive marks").wait_for()
            capture(faculty, "faculty-evaluation")
            faculty.locator("section.card input").first.fill("0.00")
            faculty.get_by_role("button", name="Save descriptive marks").click()
            faculty.locator("aside").get_by_role("button", name="Publish").last.wait_for()
            capture(faculty, "faculty-ready-to-publish")
            browser.close()
            return

        public = browser.new_page(viewport=VIEWPORT)
        public.goto(f"{BASE_URL}/login")
        capture(public, "login")
        public.goto(f"{BASE_URL}/register")
        capture(public, "student-registration")

        candidate = browser.new_page(viewport=VIEWPORT)
        candidate.goto(f"{BASE_URL}/register")
        suffix = uuid4().hex[:8]
        candidate.get_by_label("Name").fill("Report Capture Student")
        candidate.get_by_label("Email").fill(f"report.capture.{suffix}@oes.local")
        candidate.get_by_label("Password").fill("Capture@12345")
        candidate.get_by_role("button", name="Register").click()
        candidate.wait_for_url("**/login")
        login(candidate, f"report.capture.{suffix}@oes.local", "Capture@12345")
        capture(candidate, "student-dashboard")
        candidate.get_by_role("button", name="Start").click()
        candidate.wait_for_url("**/student/attempts/**")
        candidate.get_by_role("button", name="Mark for review").click()
        candidate.wait_for_timeout(500)
        capture(candidate, "exam-room")
        candidate.get_by_role("button", name="Submit paper").click()
        candidate.wait_for_timeout(500)
        capture(candidate, "submission-confirmation")

        student = browser.new_page(viewport=VIEWPORT)
        login(student, "student@oes.local", "Student@12345")
        student.goto(f"{BASE_URL}/student/results")
        capture(student, "student-result-history")
        result_link = student.get_by_role("link", name="Open").first
        if result_link.count():
            result_link.click()
            student.get_by_role("heading", name="Operating Systems Midterm").wait_for()
            capture(student, "student-result-detail")

        faculty = browser.new_page(viewport=VIEWPORT)
        login(faculty, "faculty@oes.local", "Faculty@12345")
        faculty.goto(f"{BASE_URL}/faculty/exams")
        capture(faculty, "faculty-exam-list")
        first_open = faculty.locator("article.card").filter(
            has_text="Operating Systems Midterm"
        ).get_by_role("link", name="Open")
        if first_open.count():
            first_open.click()
            faculty.get_by_role("heading", name="Operating Systems Midterm").wait_for()
            capture(faculty, "faculty-exam-editor")
        faculty.goto(f"{BASE_URL}/faculty/questions")
        capture(faculty, "question-bank")
        faculty.goto(f"{BASE_URL}/faculty/evaluation")
        needs_marking = faculty.locator("aside button.ghost").last
        needs_marking.wait_for()
        if needs_marking.count():
            needs_marking.click()
            faculty.get_by_role("button", name="Save descriptive marks").wait_for()
            capture(faculty, "faculty-evaluation")
            marks = faculty.locator("section.card input")
            if marks.count():
                marks.first.fill("0.00")
                faculty.get_by_role("button", name="Save descriptive marks").click()
                faculty.locator("aside").get_by_role("button", name="Publish").last.wait_for()
                capture(faculty, "faculty-ready-to-publish")
        else:
            capture(faculty, "faculty-evaluation")
            capture(faculty, "faculty-ready-to-publish")
        faculty.goto(f"{BASE_URL}/faculty/reports/1")
        faculty.get_by_role("heading", name="Operating Systems Midterm").wait_for()
        capture(faculty, "faculty-report")
        faculty.get_by_role("heading", name="Topic and difficulty").scroll_into_view_if_needed()
        capture(faculty, "faculty-analytics")

        admin = browser.new_page(viewport=VIEWPORT)
        login(admin, "admin@oes.local", "Admin@12345")
        capture(admin, "admin-summary")
        admin.get_by_role("table").scroll_into_view_if_needed()
        capture(admin, "admin-summary-detail")
        admin.goto(f"{BASE_URL}/admin/users")
        capture(admin, "admin-users")
        admin.goto(f"{BASE_URL}/admin/audit")
        capture(admin, "admin-audit")

        browser.close()


if __name__ == "__main__":
    main()
