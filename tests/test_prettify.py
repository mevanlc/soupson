import subprocess


def test_preserves_html_comments():
    html = "<div><!--\ncomments\n--></div>"
    result = subprocess.run(
        ["uv", "run", "soupson"],
        input=html,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "<unknown>" not in result.stdout
    assert "<!--" in result.stdout
    assert "comments" in result.stdout
    assert "-->" in result.stdout

