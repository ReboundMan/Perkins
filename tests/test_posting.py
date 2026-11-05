"""posting.py and feeds/jsonld.py: every route, with recorded fictional fixtures and no network."""
import argparse
import json
from pathlib import Path

import pytest

from perkins import posting
from perkins.feeds import http, jsonld

FIX = Path(__file__).parent / "fixtures" / "feeds"


def fixture(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def fake_http(monkeypatch, routes: dict) -> list:
    """Serve fixture text by URL; anything else is a 404. Returns the list of calls made."""
    calls = []

    def lookup(url):
        if url not in routes:
            raise http.FeedError(f"{url} answered HTTP 404")
        return routes[url]

    def get_text(url):
        calls.append(("text", url))
        return lookup(url)

    def get_json(url):
        calls.append(("json", url))
        return json.loads(lookup(url))

    def post_json(url, body):
        calls.append(("post", url))
        return json.loads(lookup(url))

    monkeypatch.setattr(http, "get_text", get_text)
    monkeypatch.setattr(http, "get_json", get_json)
    monkeypatch.setattr(http, "post_json", post_json)
    return calls


# --- JSON-LD ------------------------------------------------------------------------

def test_jsonld_single_object():
    ld = jsonld.job_posting(fixture("ashby_posting.html"))
    assert ld["title"] == "Head of Manufacturing Operations"
    assert ld["company"] == "Alder Robotics"
    assert ld["location"] == "Pittsburgh, PA, United States"
    assert ld["identifier"] == "a1b2c3d4-0000-4000-8000-000000000001"
    assert ld["datePosted"] == "2026-10-15"
    assert ld["baseSalary"] == "USD 190,000 to 230,000 per year"
    assert ld["description"].splitlines() == [
        "Alder Robotics builds warehouse robots.",
        "",
        "You will:",
        "",
        "- Run the Pittsburgh plant",
        "- Hire two plant managers",
        "",
        "We value safety above speed.",
    ]


def test_jsonld_list_with_escaped_html():
    ld = jsonld.job_posting(fixture("jsonld_list.html"))
    assert ld["title"] == "Director, Grid Planning"
    assert ld["company"] == "Kestrel Energy"
    assert ld["location"] == "Houston, TX, US; Austin, TX, US"
    assert ld["identifier"] == "KE-2201"
    assert ld["baseSalary"] == "USD 185,000 per year"
    assert ld["description"] == "Kestrel Energy plans the grid of tomorrow.\n\nYou will lead planning."


def test_jsonld_graph_with_plain_text_description():
    ld = jsonld.job_posting(fixture("jsonld_graph.html"))
    assert ld["title"] == "Chief Technology Officer"
    assert ld["company"] == "Bluewater Grid"
    assert ld["location"] == "Remote (United States)"
    assert ld["identifier"] == "BWG-77"
    assert ld["description"] == ("Bluewater Grid is hiring its first CTO.\n\n"
                                 "You will own the storage control software.\nReporting to the CEO.")


def test_jsonld_none_when_no_posting_and_bad_json_skipped():
    assert jsonld.job_posting(fixture("no_posting.html")) is None
    assert len(jsonld.blocks(fixture("no_posting.html"))) == 1  # the invalid block is skipped


def test_html_to_text_keeps_every_word_and_paragraphs():
    text = jsonld.html_to_text(
        "<div><h3>Role</h3><p>One <b>bold</b>   word,\nthen more.</p><p>Line one<br>Line two</p>"
        "<script>skip()</script><ol><li>First</li><li><p>Second</p></li></ol></div>")
    assert text == "Role\n\nOne bold word, then more.\n\nLine one\nLine two\n\n- First\n- Second"


def test_salary_text_shapes():
    assert jsonld.salary_text(None) == ""
    assert jsonld.salary_text(150000) == "150,000"
    assert jsonld.salary_text({"currency": "USD", "value": 99.5}) == "USD 99.50"
    assert jsonld.salary_text({"currency": "USD", "value": {"minValue": 80, "maxValue": 95, "unitText": "HOUR"}}) \
        == "USD 80 to 95 per hour"


# --- routes -------------------------------------------------------------------------

WD_URL = "https://pinecresthealth.wd1.myworkdayjobs.com/en-US/External/job/Boise-ID/Vice-President--Clinical-Operations_R0001"
WD_API = "https://pinecresthealth.wd1.myworkdayjobs.com/wday/cxs/pinecresthealth/External/job/Boise-ID/Vice-President--Clinical-Operations_R0001"


def test_workday_api_url_inserts_cxs_and_drops_language():
    assert posting.workday_api_url(WD_URL) == WD_API
    assert posting.workday_api_url(WD_URL.replace("/en-US", "") + "?source=board") == WD_API
    assert posting.workday_api_url("https://pinecresthealth.wd1.myworkdayjobs.com/External") is None
    assert posting.workday_api_url("https://jobs.example.com/job/1") is None


def test_workday_route(monkeypatch):
    calls = fake_http(monkeypatch, {WD_API: fixture("workday_job.json")})
    post = posting.fetch_posting(WD_URL)
    assert calls == [("json", WD_API)]
    assert post["source"] == "workday"
    assert post["title"] == "Vice President, Clinical Operations"
    assert post["company"] == "Pinecrest Health"
    assert post["location"] == "Boise, ID; Nampa, ID"
    assert post["req_id"] == "R0001"
    assert post["url"] == WD_URL
    assert "- Run clinical operations across four sites" in post["description"]
    assert "Pinecrest Health is looking for a Vice President of Clinical Operations.\n\nWhat you will do:" \
        in post["description"]


def test_workday_falls_back_to_page_jsonld(monkeypatch):
    fake_http(monkeypatch, {WD_URL: fixture("jsonld_graph.html")})
    post = posting.fetch_posting(WD_URL)
    assert post["source"] == "jsonld"
    assert post["title"] == "Chief Technology Officer"


GH_API = "https://boards-api.greenhouse.io/v1/boards/larkspuranalytics/jobs/4001001001"


@pytest.mark.parametrize("url", [
    "https://job-boards.greenhouse.io/larkspuranalytics/jobs/4001001001",
    "https://boards.greenhouse.io/larkspuranalytics/jobs/4001001001?gh_src=abc",
    "https://boards.greenhouse.io/embed/job_app?for=larkspuranalytics&token=4001001001",
])
def test_greenhouse_route(monkeypatch, url):
    calls = fake_http(monkeypatch, {GH_API: fixture("greenhouse_job.json")})
    post = posting.fetch_posting(url)
    assert calls == [("json", GH_API)]
    assert post["source"] == "greenhouse"
    assert post["title"] == "VP, Data Platform"
    assert post["company"] == "Larkspur Analytics"
    assert post["location"] == "Remote, United States"
    assert post["req_id"] == "LA-101"
    assert post["description"].splitlines() == [
        "About the role",
        "",
        "Larkspur Analytics is hiring a VP to run the data platform & its team.",
        "",
        "- Own the platform roadmap",
        "- Lead three engineering managers",
        "",
        "Base pay range: $210,000 to $250,000.",
    ]


def test_greenhouse_gh_jid_on_company_careers_page(monkeypatch):
    url = "https://careers.larkspur.example/open-roles?gh_jid=4001001001"
    calls = fake_http(monkeypatch, {url: fixture("careers_gh_jid.html"), GH_API: fixture("greenhouse_job.json")})
    post = posting.fetch_posting(url)
    assert calls == [("text", url), ("json", GH_API)]
    assert post["source"] == "greenhouse"
    assert post["url"] == url
    assert post["title"] == "VP, Data Platform"


def test_ashby_route_reads_page_jsonld_not_board_api(monkeypatch):
    url = "https://jobs.ashbyhq.com/alderrobotics/a1b2c3d4-0000-4000-8000-000000000001"
    calls = fake_http(monkeypatch, {url: fixture("ashby_posting.html")})
    post = posting.fetch_posting(url)
    assert calls == [("text", url)]
    assert post["source"] == "ashby"
    assert post["company"] == "Alder Robotics"
    assert post["req_id"] == "a1b2c3d4-0000-4000-8000-000000000001"
    assert "- Hire two plant managers" in post["description"]
    assert post["notes"] == "Base pay listed: USD 190,000 to 230,000 per year. Posted 2026-10-15."


ICIMS_URL = "https://careers-pinecresthealth.icims.com/jobs/2201/director-of-supply-chain/job"


def test_icims_route_uses_iframe_page_text(monkeypatch):
    frame = ICIMS_URL + "?in_iframe=1"
    calls = fake_http(monkeypatch, {frame: fixture("icims_full.html")})
    post = posting.fetch_posting(ICIMS_URL + "?mode=job&iis=Job+Board")
    assert calls == [("text", frame)]
    assert post["source"] == "icims"
    assert post["title"] == "Director of Supply Chain (2201) - Pinecrest Health Careers"
    assert post["req_id"] == "2201"
    text = post["description"]
    assert "Overview\n\nPinecrest Health is a regional health system" in text
    assert "- Own the annual supply budget, vendor contracts, and the group purchasing relationship." in text
    assert "ignore me" not in text and "margin" not in text


def test_icims_thin_page_uses_jsonld(monkeypatch):
    url = "https://careers-pinecresthealth.icims.com/jobs/2202/head-of-patient-experience/job"
    fake_http(monkeypatch, {url + "?in_iframe=1": fixture("icims_thin.html")})
    post = posting.fetch_posting(url)
    assert post["source"] == "icims"
    assert post["title"] == "Head of Patient Experience"
    assert post["company"] == "Pinecrest Health"
    assert post["location"] == "Boise, ID, US"
    assert post["req_id"] == "2202"
    assert post["description"] == ("Pinecrest Health wants a Head of Patient Experience.\n\n"
                                   "You will own patient surveys and service recovery.")


def test_other_site_uses_jsonld(monkeypatch):
    url = "https://careers.kestrel.example/jobs/2201"
    fake_http(monkeypatch, {url: fixture("jsonld_list.html")})
    post = posting.fetch_posting(url)
    assert post["source"] == "jsonld"
    assert post["title"] == "Director, Grid Planning"
    assert post["req_id"] == "KE-2201"
    assert post["notes"] == "Base pay listed: USD 185,000 per year. Posted 2026-10-30."


def test_no_description_says_open_in_browser_or_paste(monkeypatch):
    url = "https://careers.alder.example/jobs/9"
    fake_http(monkeypatch, {url: fixture("no_posting.html")})
    with pytest.raises(posting.PostingError) as e:
        posting.fetch_posting(url)
    assert "browser" in str(e.value) and "paste" in str(e.value)


def test_unreachable_page_is_a_posting_error(monkeypatch):
    fake_http(monkeypatch, {})
    with pytest.raises(posting.PostingError) as e:
        posting.fetch_posting("https://careers.alder.example/jobs/10")
    assert "HTTP 404" in str(e.value)
    with pytest.raises(posting.PostingError):
        posting.fetch_posting("not a url")


# --- CLI ----------------------------------------------------------------------------

def test_cli_text_and_json(monkeypatch, capsys):
    url = "https://careers.kestrel.example/jobs/2201"
    fake_http(monkeypatch, {url: fixture("jsonld_list.html")})
    assert posting.cli(argparse.Namespace(url=url, json=False), None) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "Director, Grid Planning at Kestrel Energy (Houston, TX, US; Austin, TX, US)"
    assert out[1] == ""
    assert out[2] == "Kestrel Energy plans the grid of tomorrow."
    assert posting.cli(argparse.Namespace(url=url, json=True), None) == 0
    data = json.loads(capsys.readouterr().out)
    assert set(data) == {"title", "company", "location", "req_id", "description", "source", "url", "notes"}


def test_add_arguments():
    p = argparse.ArgumentParser()
    posting.add_arguments(p)
    args = p.parse_args(["https://careers.kestrel.example/jobs/2201", "--json"])
    assert args.json and args.url.endswith("/2201")
