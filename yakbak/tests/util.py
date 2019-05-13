from typing import Pattern, Union
import re

from flask import Response


def assert_html_response(resp: Response, status: int = 200) -> str:
    """
    Ensure ``resp`` has certain common HTTP headers for HTML responses.

    Returns the decoded HTTP response body.

    """
    assert resp.status_code == status, f"got {resp.status_code}"
    assert resp.headers["Content-Type"].startswith("text/html")
    if status == 200:
        assert "charset" in resp.headers["Content-Type"]

    data = resp.data
    assert resp.content_length == len(data)

    return data.decode(resp.charset or "utf8")


def assert_html_response_contains(
    resp: Response, *snippets: Union[str, Pattern], status: int = 200
) -> None:
    """
    Ensure that each of the ``snippets`` is in the body of ``resp``.

    """
    content = assert_html_response(resp, status)
    for snippet in snippets:
        if isinstance(snippet, Pattern):
            assert re.search(
                snippet, content
            ), f"{snippet!r} does not match {content!r}"
        else:
            assert snippet in content


def assert_html_response_doesnt_contain(
    resp: Response, *snippets: Union[str, Pattern], status: int = 200
) -> None:
    """
    Ensure that none of the ``snippets`` is in the body of ``resp``.

    """
    content = assert_html_response(resp, status)
    for snippet in snippets:
        if isinstance(snippet, Pattern):
            assert not re.search(
                snippet, content
            ), f"{snippet!r} should not match {content!r}"
        else:
            assert snippet not in content


def assert_redirected(resp: Response, to: str) -> None:
    assert_html_response(resp, 302)

    landing_url = f"http://localhost{to}"
    assert resp.headers["Location"] == landing_url


def extract_csrf_from(resp: Response) -> str:
    data = resp.data
    body = data.decode(resp.mimetype_params["charset"])
    tags = re.findall('(<input[^>]*type="hidden"[^>]*>)', body)
    assert len(tags) == 1
    match = re.search('value="([^"]*)"', tags[0])
    assert match, "CSRF hidden input had no value"
    return match.group(1)
