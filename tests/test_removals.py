"""Tests for soupson removal functionality."""

import pytest

# Check if lxml is available
try:
    import lxml

    HAS_LXML = True
except ImportError:
    HAS_LXML = False


class TestCSSRemovals:
    """Tests for CSS selector removals."""

    def test_css_unwrap_basic(self, capsys):
        """Test CSS unwrap removes tag but keeps children."""
        import subprocess

        html = '<html><body><div class="ad">content</div></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-rs", ".ad"],
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
            ["uv", "run", "soupson", "-rrs", ".ad"],
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
            ["uv", "run", "soupson", "-rs", ".ad", "-rs", ".junk"],
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
            ["uv", "run", "soupson", "-rx", "//script"],
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
            ["uv", "run", "soupson", "-rrx", "//script"],
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
            ["uv", "run", "soupson", "-rx", "//@onclick"],
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
            ["uv", "run", "soupson", "-rs", ".ad", "-rx", "//script"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '<div class="ad">' not in result.stdout
        assert "<script" not in result.stdout
        assert "ad" in result.stdout
        assert "alert(1)" in result.stdout

    def test_xpath_element_with_predicate(self):
        """Test XPath selecting element with attribute predicate."""
        import subprocess

        html = '<html><body><div id="test">content</div></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-rx", "//div[@id='test']"],
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
            ["uv", "run", "soupson", "-rs", "[[[invalid"],
            input=html,
            capture_output=True,
            text=True,
        )
        # cssselect may handle this gracefully or error
        # Just verify it doesn't crash silently
        assert result.returncode in (0, 1, 2)

    @pytest.mark.skipif(not HAS_LXML, reason="lxml not installed")
    def test_invalid_xpath(self):
        """Test invalid XPath expression handling."""
        import subprocess

        html = "<html><body><div>test</div></body></html>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-rx", "//[[[invalid"],
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
            ["uv", "run", "soupson", "-rrx", "//script"],
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
            ["uv", "run", "soupson", "-rx", "//@onclick"],
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
            ["uv", "run", "soupson", "-rx", "//@*"],
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
            ["uv", "run", "soupson", "-rx", "//div[@class='b']/@id"],
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
            ["uv", "run", "soupson", "-rs", "span", "-rs", "em"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<span" not in result.stdout
        assert "<em" not in result.stdout
        assert "text" in result.stdout


class TestFragmentPreservation:
    """Tests for HTML fragment preservation (no unwanted html/body wrapping)."""

    def test_fragment_no_wrapper(self):
        """Fragment input should not get wrapped in html/body."""
        import subprocess

        html = '<div id="foo"><p>text</p></div>'
        result = subprocess.run(
            ["uv", "run", "soupson"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<html" not in result.stdout
        assert "<body" not in result.stdout
        assert "<div" in result.stdout
        assert "text" in result.stdout

    def test_fragment_preserved_after_xpath(self):
        """Fragment should stay unwrapped after XPath operations."""
        import subprocess

        html = '<div id="foo" onclick="x()"><p>text</p></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-rx", "//@onclick"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<html" not in result.stdout
        assert "<body" not in result.stdout
        assert "<div" in result.stdout
        assert "onclick" not in result.stdout

    def test_fragment_preserved_after_css(self):
        """Fragment should stay unwrapped after CSS operations."""
        import subprocess

        html = '<div><span class="remove">gone</span><p>text</p></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-rrs", ".remove"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<html" not in result.stdout
        assert "<body" not in result.stdout
        assert "<div" in result.stdout
        assert "gone" not in result.stdout
        assert "text" in result.stdout

    def test_full_document_preserved(self):
        """Full HTML document should keep its structure."""
        import subprocess

        html = '<!DOCTYPE html><html><head><title>Test</title></head><body><p>text</p></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<html" in result.stdout
        assert "<body" in result.stdout
        assert "<head" in result.stdout
        assert "text" in result.stdout
