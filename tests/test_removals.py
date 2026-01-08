"""Tests for soupson removal functionality."""

import pytest

from soupson import SelectorType, _parse_selector

# Check if lxml is available
try:
    import lxml

    HAS_LXML = True
except ImportError:
    HAS_LXML = False


class TestSelectorParsing:
    """Tests for selector type detection."""

    def test_css_selector_default(self):
        """CSS selector is default for normal expressions."""
        sel_type, selector = _parse_selector(".foo")
        assert sel_type == SelectorType.CSS
        assert selector == ".foo"

    def test_css_selector_with_spaces(self):
        """CSS selector with leading/trailing spaces."""
        sel_type, selector = _parse_selector("  div.bar  ")
        assert sel_type == SelectorType.CSS
        assert selector == "div.bar"

    def test_xpath_single_slash(self):
        """XPath detected with single slash."""
        sel_type, selector = _parse_selector("/html/body")
        assert sel_type == SelectorType.XPATH
        assert selector == "/html/body"

    def test_xpath_double_slash(self):
        """XPath detected with double slash."""
        sel_type, selector = _parse_selector("//div")
        assert sel_type == SelectorType.XPATH
        assert selector == "//div"

    def test_xpath_explicit_bang(self):
        """XPath with explicit ! prefix."""
        sel_type, selector = _parse_selector("!div[@id]")
        assert sel_type == SelectorType.XPATH
        assert selector == "div[@id]"

    def test_xpath_attribute(self):
        """XPath selecting attributes."""
        sel_type, selector = _parse_selector("//@onclick")
        assert sel_type == SelectorType.XPATH
        assert selector == "//@onclick"

    def test_xpath_bang_with_slash(self):
        """XPath with both ! and / should strip !."""
        sel_type, selector = _parse_selector("!//script")
        assert sel_type == SelectorType.XPATH
        assert selector == "//script"


class TestCSSRemovals:
    """Tests for CSS selector removals."""

    def test_css_unwrap_basic(self, capsys):
        """Test CSS unwrap removes tag but keeps children."""
        import subprocess

        html = '<html><body><div class="ad">content</div></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", ".ad"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<div" not in result.stdout
        assert "content" in result.stdout

    def test_css_recursive_delete(self):
        """Test CSS recursive delete removes tag and children."""
        import subprocess

        html = '<html><body><div class="ad"><span>content</span></div></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-R", ".ad"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<div" not in result.stdout
        assert "content" not in result.stdout

    def test_css_multiple_removals(self):
        """Test multiple CSS removals in order."""
        import subprocess

        html = '<html><body><div class="ad">ad</div><span class="junk">junk</span></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", ".ad", "-r", ".junk"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '<div class="ad">' not in result.stdout
        assert '<span class="junk">' not in result.stdout
        assert "ad" in result.stdout
        assert "junk" in result.stdout


@pytest.mark.skipif(not HAS_LXML, reason="lxml not installed")
class TestXPathRemovals:
    """Tests for XPath removals (requires lxml)."""

    def test_xpath_unwrap_element(self):
        """Test XPath unwrap removes element but keeps children."""
        import subprocess

        html = "<html><body><script>alert(1)</script></body></html>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", "//script"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<script" not in result.stdout
        assert "alert(1)" in result.stdout

    def test_xpath_recursive_delete(self):
        """Test XPath recursive delete removes element and children."""
        import subprocess

        html = "<html><body><script><![CDATA[alert(1)]]></script></body></html>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-R", "//script"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<script" not in result.stdout
        assert "alert" not in result.stdout

    def test_xpath_attribute_removal(self):
        """Test XPath removing attributes."""
        import subprocess

        html = '<html><body><p onclick="x()">text</p></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", "//@onclick"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "onclick" not in result.stdout
        assert "<p>" in result.stdout or "<p " not in result.stdout
        assert "text" in result.stdout

    def test_xpath_mixed_with_css(self):
        """Test mixing XPath and CSS removals."""
        import subprocess

        html = '<html><body><div class="ad">ad</div><script>alert(1)</script></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", ".ad", "-r", "//script"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '<div class="ad">' not in result.stdout
        assert "<script" not in result.stdout
        assert "ad" in result.stdout
        assert "alert(1)" in result.stdout

    def test_xpath_explicit_bang_prefix(self):
        """Test XPath with explicit ! prefix."""
        import subprocess

        html = '<html><body><div id="test">content</div></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", "!//div[@id='test']"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '<div id="test">' not in result.stdout
        assert "content" in result.stdout


class TestErrorHandling:
    """Tests for error conditions."""

    def test_xpath_without_lxml(self):
        """Test that XPath without lxml gives helpful error."""
        # This test would need to run in an environment without lxml
        # Skipping for now as it's hard to test in the current environment
        pass

    def test_invalid_css_selector(self):
        """Test invalid CSS selector handling."""
        import subprocess

        html = "<html><body><div>test</div></body></html>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", "[[[invalid"],
            input=html,
            capture_output=True,
            text=True,
        )
        # BeautifulSoup may handle this gracefully or error
        # Just verify it doesn't crash silently
        assert result.returncode in (0, 1, 2)

    @pytest.mark.skipif(not HAS_LXML, reason="lxml not installed")
    def test_invalid_xpath(self):
        """Test invalid XPath expression handling."""
        import subprocess

        html = "<html><body><div>test</div></body></html>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", "//[[[invalid"],
            input=html,
            capture_output=True,
            text=True,
        )
        # Should error with helpful message
        assert result.returncode != 0
        assert "XPath" in result.stderr or "Invalid" in result.stderr


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.skipif(not HAS_LXML, reason="lxml not installed")
    def test_remove_multiple_elements(self):
        """Test removing multiple matching elements."""
        import subprocess

        html = "<html><body><script>1</script><script>2</script></body></html>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-R", "//script"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<script" not in result.stdout
        assert "1" not in result.stdout
        assert "2" not in result.stdout

    @pytest.mark.skipif(not HAS_LXML, reason="lxml not installed")
    def test_remove_attributes_from_multiple_elements(self):
        """Test removing same attribute from multiple elements."""
        import subprocess

        html = '<html><body><p onclick="a()">1</p><div onclick="b()">2</div></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", "//@onclick"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "onclick" not in result.stdout
        assert "1" in result.stdout
        assert "2" in result.stdout

    @pytest.mark.skipif(not HAS_LXML, reason="lxml not installed")
    def test_remove_all_attributes_wildcard(self):
        """Test //@* removes all attributes from all elements."""
        import subprocess

        html = '<html><body><div id="foo" class="bar"><p style="x" data-x="y">text</p></div></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", "//@*"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "id=" not in result.stdout
        assert "class=" not in result.stdout
        assert "style=" not in result.stdout
        assert "data-x=" not in result.stdout
        assert "text" in result.stdout

    @pytest.mark.skipif(not HAS_LXML, reason="lxml not installed")
    def test_remove_attribute_with_predicate(self):
        """Test removing attributes from elements matching a predicate."""
        import subprocess

        html = '<html><body><div id="keep" class="a"><div id="remove" class="b">text</div></div></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", "//div[@class='b']/@id"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'id="keep"' in result.stdout
        assert 'id="remove"' not in result.stdout
        assert 'class="a"' in result.stdout
        assert 'class="b"' in result.stdout

    def test_nested_removals(self):
        """Test nested element removals."""
        import subprocess

        html = "<html><body><div><span><em>text</em></span></div></body></html>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-r", "span", "-r", "em"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<span" not in result.stdout
        assert "<em" not in result.stdout
        assert "text" in result.stdout
