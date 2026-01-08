"""Tests for soupson substitution functionality."""

import subprocess


class TestXPathSubstitution:
    """Tests for XPath-based substitutions."""

    def test_xpath_substitute_attribute_value(self):
        """Test substituting in attribute values via XPath."""
        html = '<a href="http://example.com">link</a>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-sx", "//@href", "http:", "https:"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'href="https://example.com"' in result.stdout

    def test_xpath_substitute_multiple_attrs(self):
        """Test substituting in multiple matching attributes."""
        html = '<div><a href="http://a.com">a</a><a href="http://b.com">b</a></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-sx", "//@href", "http://", "https://"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'href="https://a.com"' in result.stdout
        assert 'href="https://b.com"' in result.stdout

    def test_xpath_substitute_with_backreference(self):
        """Test regex backreferences in replacement."""
        html = '<img src="image.jpg" alt="photo">'
        result = subprocess.run(
            ["uv", "run", "soupson", "-sx", "//@src", r"(\w+)\.jpg", r"\1.webp"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'src="image.webp"' in result.stdout

    def test_xpath_substitute_specific_attr(self):
        """Test substituting only in specific attribute."""
        html = '<a href="http://x.com" title="http://y.com">link</a>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-sx", "//@href", "http:", "https:"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'href="https://x.com"' in result.stdout
        assert 'title="http://y.com"' in result.stdout  # unchanged


class TestCSSSubstitution:
    """Tests for CSS selector-based substitutions."""

    def test_css_substitute_attribute_value(self):
        """Test substituting in attribute via CSS selector."""
        html = '<a class="external" href="http://example.com">link</a>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-sc", "a.external", "href", "http:", "https:"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'href="https://example.com"' in result.stdout

    def test_css_substitute_only_matching_elements(self):
        """Test that only elements matching selector are modified."""
        html = '<div><a class="ext" href="http://a.com">a</a><a href="http://b.com">b</a></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-sc", "a.ext", "href", "http:", "https:"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'href="https://a.com"' in result.stdout
        assert 'href="http://b.com"' in result.stdout  # unchanged

    def test_css_substitute_missing_attr_no_error(self):
        """Test that missing attribute doesn't cause error."""
        html = '<a class="x">no href</a>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-sc", "a.x", "href", "foo", "bar"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "no href" in result.stdout


class TestRegexSubstitution:
    """Tests for regex-based substitutions."""

    def test_regex_substitute_element_names(self):
        """Test renaming element tags via regex."""
        html = '<div><boldtext>hello</boldtext></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-se", "e", "boldtext", "strong"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "<strong>" in result.stdout
        assert "</strong>" in result.stdout
        assert "<boldtext" not in result.stdout

    def test_regex_substitute_attr_names(self):
        """Test renaming attribute names via regex."""
        html = '<div data-old="value">text</div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-se", "a", "data-old", "data-new"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'data-new="value"' in result.stdout
        assert "data-old" not in result.stdout

    def test_regex_substitute_attr_values(self):
        """Test substituting in attribute values via regex."""
        html = '<a href="http://example.com?utm_source=foo">link</a>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-se", "v", r"\?utm_[^\"]*", ""],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'href="http://example.com"' in result.stdout
        assert "utm_source" not in result.stdout

    def test_regex_substitute_multiple_elements(self):
        """Test regex substitution affects all matching elements."""
        html = '<div><foo>a</foo><foo>b</foo><bar>c</bar></div>'
        result = subprocess.run(
            ["uv", "run", "soupson", "-se", "e", "foo", "baz"],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.count("<baz>") == 2
        assert "<foo>" not in result.stdout
        assert "<bar>" in result.stdout  # unchanged


class TestSubstitutionChaining:
    """Tests for multiple substitutions in one command."""

    def test_multiple_substitutions(self):
        """Test chaining multiple substitutions."""
        html = '<a href="http://example.com" class="old">link</a>'
        result = subprocess.run(
            [
                "uv", "run", "soupson",
                "-sx", "//@href", "http:", "https:",
                "-sc", "a", "class", "old", "new",
            ],
            input=html,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert 'href="https://example.com"' in result.stdout
        assert 'class="new"' in result.stdout
