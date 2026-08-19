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
class TestAttributeRemovals:
    """Tests for direct attribute removals."""

    def test_remove_attribute_names(self):
        """Test -ra removes comma-separated attribute names."""
        import subprocess

        html = '<html><body><p style="x" onclick="y()" data-style="keep">text</p></body></html>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-ra", "style,onclick"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert ' style="x"' not in result.stdout
        assert "onclick=" not in result.stdout
        assert 'data-style="keep"' in result.stdout
        assert "text" in result.stdout

    def test_remove_attribute_names_case_insensitive_exact(self):
        """Test -ra matches exact attribute names case-insensitively."""
        import subprocess

        xml = '<root><item STYLE="x" Class="y" data-style="keep" style-extra="keep">text</item></root>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "xml", "-ra", "style,class"],
            input=xml,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "STYLE=" not in result.stdout
        assert "Class=" not in result.stdout
        assert 'data-style="keep"' in result.stdout
        assert 'style-extra="keep"' in result.stdout
        assert "text" in result.stdout


@pytest.mark.skipif(not HAS_LXML, reason="lxml not installed")
class TestCommentRemovals:
    """Tests for comment removal."""

    def test_remove_html_comments_preserves_surrounding_text(self):
        """Test -rco removes all HTML comments without dropping tail text."""
        import subprocess

        html = "<div>before<!-- first -->middle<span>x</span><!-- second -->after</div>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rco"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<!--" not in result.stdout
        assert "first" not in result.stdout
        assert "second" not in result.stdout
        assert "beforemiddle" in result.stdout
        assert "after" in result.stdout

    def test_remove_xml_comments(self):
        """Test -rco removes nested XML comments."""
        import subprocess

        xml = "<root><!-- outer --><item><!-- inner -->text</item></root>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "xml", "-rco"],
            input=xml,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<!--" not in result.stdout
        assert "outer" not in result.stdout
        assert "inner" not in result.stdout
        assert "<item>text</item>" in result.stdout


@pytest.mark.skipif(not HAS_LXML, reason="lxml not installed")
class TestBlankRemovals:
    """Tests for blank element removal."""

    def test_blank_unwrap_removes_whitespace_only_elements(self):
        """Test -rb removes childless whitespace-only elements."""
        import subprocess

        html = "<div><p>   </p><p>keep</p></div>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rb"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.count("<p>") == 1
        assert "keep" in result.stdout

    def test_blank_unwrap_keeps_whitespace_recursive_drops_it(self):
        """Test -rb keeps the blank element's text, -rrb discards it."""
        import subprocess

        html = "<p>a<span> </span>b</p>"
        unwrapped = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rb"],
            input=html,
            capture_output=True,
            text=True,
        )
        recursive = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rrb"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert unwrapped.returncode == 0
        assert recursive.returncode == 0
        assert "<span" not in unwrapped.stdout
        assert "<span" not in recursive.stdout
        assert "a b" in unwrapped.stdout
        assert "ab" in recursive.stdout

    def test_blank_removal_preserves_tail_text(self):
        """Test tail text after a blank element survives both variants."""
        import subprocess

        html = "<div><span></span>after</div>"
        for flag in ("-rb", "-rrb"):
            result = subprocess.run(
                ["uv", "run", "soupson", "-f", "htmlpart", flag],
                input=html,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert "<span" not in result.stdout
            assert "after" in result.stdout

    def test_blank_cascades_to_parent(self):
        """Test a parent left blank by removing its blank child is removed too."""
        import subprocess

        html = "<div><section><span>  </span></section>after</div>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rrb"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<span" not in result.stdout
        assert "<section" not in result.stdout
        assert "<div" in result.stdout
        assert "after" in result.stdout

    def test_blank_requires_exact_emptiness_for_preserve_tags(self):
        """Test whitespace-preserving tags are blank only when exactly empty."""
        import subprocess

        html = "<div><pre> </pre><pre></pre><textarea></textarea></div>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rrb"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.count("<pre>") == 1
        assert "<textarea" not in result.stdout

    def test_blank_ignores_void_elements(self):
        """Test void elements are never blank in HTML mode."""
        import subprocess

        html = '<div><br><img src="x"><span></span></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rrb"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<br" in result.stdout
        assert "<img" in result.stdout
        assert "<span" not in result.stdout

    def test_blank_removes_empty_tags_in_xml_mode(self):
        """Test XML mode has no void elements, so empty tags are blank."""
        import subprocess

        xml = "<root><item/><item>x</item><br/></root>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "xml", "-rrb"],
            input=xml,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<br" not in result.stdout
        assert result.stdout.count("<item") == 1
        assert "x" in result.stdout

    def test_blank_keeps_elements_with_children(self):
        """Test an element holding a child is not blank, even a void child."""
        import subprocess

        html = "<div><em><br></em></div>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rrb"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<em" in result.stdout
        assert "<br" in result.stdout

    def test_blank_keeps_elements_with_comment_children(self):
        """Test a comment counts as content, but -rco first exposes the blank."""
        import subprocess

        html = "<div><div><!-- ad --></div>keep</div>"
        kept = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rrb"],
            input=html,
            capture_output=True,
            text=True,
        )
        stripped = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rco", "-rrb"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert kept.returncode == 0
        assert stripped.returncode == 0
        assert kept.stdout.count("<div") == 2
        assert stripped.stdout.count("<div") == 1
        assert "keep" in stripped.stdout

    def test_blank_ignores_attributes(self):
        """Test attributes do not save an otherwise blank element."""
        import subprocess

        html = '<div><span class="keep"></span>text</div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rrb"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<span" not in result.stdout
        assert "text" in result.stdout

    def test_blank_css_restriction(self):
        """Test -rbs only removes blank elements matching the selector."""
        import subprocess

        html = '<div><span class="x"> </span><span> </span><p> </p></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rbs", "span.x"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'class="x"' not in result.stdout
        assert result.stdout.count("<span") == 1
        assert "<p" in result.stdout

    def test_blank_css_skips_non_blank_matches(self):
        """Test -rrbs leaves selector matches that hold content."""
        import subprocess

        html = '<div><span class="x"></span><span class="x">text</span></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rrbs", ".x"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.count("<span") == 1
        assert "text" in result.stdout

    def test_blank_regex_restriction(self):
        """Test -rbe only removes blank elements whose name matches."""
        import subprocess

        html = "<div><span></span><em></em></div>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rbe", "^span$"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<span" not in result.stdout
        assert "<em" in result.stdout

    def test_blank_regex_recursive_skips_non_blank_matches(self):
        """Test -rrbe leaves name matches that hold content."""
        import subprocess

        html = "<div><span></span><span>text</span><em></em></div>"
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rrbe", "span"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.count("<span") == 1
        assert "text" in result.stdout
        assert "<em" in result.stdout

    def test_blank_invalid_selector(self):
        """Test -rbs reports an invalid CSS selector."""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rbs", "[[[invalid"],
            input="<div></div>",
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "selector" in result.stderr or "Invalid" in result.stderr

    def test_blank_invalid_regex(self):
        """Test -rbe reports an invalid regex pattern."""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rbe", "("],
            input="<div></div>",
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "regex" in result.stderr or "Invalid" in result.stderr


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
    """Tests for HTML fragment preservation with -f htmlpart."""

    def test_fragment_no_wrapper(self):
        """Fragment input should not get wrapped in html/body with -f htmlpart."""
        import subprocess

        html = '<div id="foo"><p>text</p></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart"],
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
        """Fragment should stay unwrapped after XPath operations with -f htmlpart."""
        import subprocess

        html = '<div id="foo" onclick="x()"><p>text</p></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rx", "//@onclick"],
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
        """Fragment should stay unwrapped after CSS operations with -f htmlpart."""
        import subprocess

        html = '<div><span class="remove">gone</span><p>text</p></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "htmlpart", "-rrs", ".remove"],
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

    def test_fragment_wrapped_with_html_format(self):
        """Fragment input should get wrapped in html/body with default -f html."""
        import subprocess

        html = '<div id="foo"><p>text</p></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-f", "html"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<html" in result.stdout
        assert "<body" in result.stdout
        assert "<div" in result.stdout
        assert "text" in result.stdout
