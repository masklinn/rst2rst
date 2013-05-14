"""rst2rst tests."""
from difflib import unified_diff
import os
import re
from unittest import TestCase

from docutils.core import publish_string


class PEP396TestCase(TestCase):
    """Check's PEP 396 compliance, i.e. package's __version__ attribute."""
    def get_version(self):
        """Return rst2rst.__version__."""
        from rst2rst import __version__
        return __version__

    def test_version_present(self):
        """Check that rst2rst.__version__ exists."""
        try:
            version = self.get_version()
        except ImportError:
            self.fail('rst2rst package has no attribute __version__.')

    def test_version_match(self):
        """Check that rst2rst.__version__ matches pkg_resources information."""
        try:
            import pkg_resources
        except ImportError:
            self.fail('Cannot import pkg_resources module. It is part of ' \
                      'setuptools, which is a dependency of rst2rst.')
        installed_version = pkg_resources.get_distribution('rst2rst').version
        self.assertEqual(installed_version, self.get_version(),
                         'Version mismatch: version.txt tells "%s" whereas ' \
                         'pkg_resources tells "%s". ' \
                         'YOU MAY NEED TO RUN ``make update`` to update the ' \
                         'installed version in development environment.' \
                         % (self.get_version(), installed_version))

FILE_DIR = os.path.normpath(
    os.path.abspath(
        os.path.dirname(__file__)))
FIXTURES_DIR = os.path.join(FILE_DIR, 'fixtures')
class TestMeta(type):
    """ Unittest is a pain in the ass: it calls dir() on the *class*,
    and then goes and gets each found method (on the class again) to
    check that they're actually callables. But the calling itself is
    performed on the instance.

    And of course fail() needs an instance, so the actual fixture
    runner has to be on the instance. And thus __getattr__ must be
    implemented on both the class (via metaclass) and the instance.
    """
    def __dir__(cls):
        return sorted(set(
            dir(type(cls))
            + list(cls.__dict__)
            + cls._fixture_methods()
        ))

    def __getattr__(cls, attrname):
        """ Return a dummy callable if ``attrname`` is
        ``test_$fixture`` so unittest shuts up
        """
        input_path, output_path = cls._fixture_paths(attrname)

        return lambda: None

class WriterTestCase(TestCase):
    __metaclass__ = TestMeta
    """Test suite for the rst2rst.writer.Writer class."""
    @classmethod
    def _fixture_methods(cls):
        """ Lists the names of all fixtures in the ./fixtures
        directory (*-input.txt files with the -input.txt part
        stripped), returns them as test_-prefixed names so unittest
        believes they're test methods
        """
        return [
            re.sub(r'^(.+?)-input\.txt$', r'test_\1', f)
            for f in os.listdir(FIXTURES_DIR)
            if f.endswith('-input.txt')
        ]
    @classmethod
    def _fixture_paths(cls, attrname):
        """ For a fixture named $fixture, gets the corresponding
        -input and -output files paths and asserts both exist. The
        attribute fetched should be test_$fixture
        """
        if not attrname.startswith('test_'):
            raise AttributeError("'%s' object has no attribute '%s'" % (
                cls.__name__, attrname))

        fixture = attrname.replace('test_', '', 1)
        
        fixture_input = '%s-input.txt' % fixture
        input_path = os.path.join(FIXTURES_DIR, fixture_input)
        if not os.path.exists(input_path):
            raise AttributeError("Missing input file '%s' for fixture %s" % (
                fixture_input, fixture))

        fixture_result = '%s-output.txt' % fixture
        result_path = os.path.join(FIXTURES_DIR, fixture_result)
        if not os.path.exists(result_path):
            raise AttributeError("Missing result file '%s' for fixture %s" % (
                fixture_result, fixture))

        return input_path, result_path

    def __getattr__(self, attrname):
        input_path, output_path = self._fixture_paths(attrname)

        return lambda: self.run_fixture(input_path, output_path)

    def run_fixture(self, fixture_input, fixture_expectation):
        """ Runs the rst2rst writer on ``fixture_input`` and asserts
        the result matches ``fixture_expectation``
        """
        with open(fixture_input) as input_file:
            input_str = input_file.read()
        output = publish_string(source=input_str, writer_name='rst2rst')

        with open(fixture_expectation) as expectation_file:
            expected = expectation_file.read()

        if output != expected:
            output_lines = output.replace('\n', '\\n\n').splitlines(True)
            expected_lines = expected.replace('\n', '\\n\n').splitlines(True)

            diff = ''.join(unified_diff(expected_lines, output_lines))
            msg = "Content generated from %s differs from content at %s" \
            "\nDiff:\n%s" % (
                os.path.basename(fixture_input),
                os.path.basename(fixture_expectation),
                diff
            )
            self.fail(msg)

    def test_repeatability(self):
        """Make sure that a converted document keeps the same if converted
        again."""