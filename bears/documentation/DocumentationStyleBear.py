from coalib.bearlib.languages.documentation.DocumentationComment import (
    DocumentationComment)
from coalib.bearlib.languages.documentation.DocstyleDefinition import (
    DocstyleDefinition)
from coalib.bearlib.languages.documentation.DocBaseClass import (
    DocBaseClass)
from coalib.bears.LocalBear import LocalBear
from coalib.results.Result import Result

from textwrap import dedent


class DocumentationStyleBear(DocBaseClass, LocalBear):
    LANGUAGES = {language for docstyle, language in
                 DocstyleDefinition.get_available_definitions()}
    AUTHORS = {'The coala developers'}
    AUTHORS_EMAILS = {'coala-devel@googlegroups.com'}
    LICENSE = 'AGPL-3.0'
    ASCIINEMA_URL = 'https://asciinema.org/a/7sfk3i9oxs1ixg2ncsu3pym0u'
    CAN_DETECT = {'Documentation'}
    CAN_FIX = {'Documentation'}

    def process_documentation(self,
                              parsed,
                              allow_missing_func_desc: str=False,
                              indent_size: int=4,
                              expand_one_liners: str=False):
        """
        This fixes the parsed documentation comment.

        :param parsed:
            Contains parsed documentation comment.
        :param allow_missing_func_desc:
            When set ``True`` this will allow functions with missing
            descriptions, allowing functions to start with params.
        :param indent_size:
            Number of spaces per indentation level.
        :param expand_one_liners:
            When set ``True`` this will expand one liner docstrings.
        :return:
            A tuple of fixed parsed documentation comment and warning_desc.
        """
        # Assuming that the first element is always the only main
        # description.
        metadata = iter(parsed)

        main_description = next(metadata)

        if main_description.desc == '\n' and not allow_missing_func_desc:
            # Triple quoted string literals doesn't look good. It breaks
            # the line of flow. Hence we use dedent.
            warning_desc = dedent("""\
            Missing function description.
            Please set allow_missing_func_desc = True to ignore this warning.
            """)
        else:
            warning_desc = 'Documentation does not have correct style.'

        # one empty line shall follow main description (except it's empty
        # or no annotations follow).
        if main_description.desc.strip() != '':
            if not expand_one_liners and len(parsed) == 1:
                main_description = main_description._replace(
                    desc=main_description.desc.strip())
            else:
                main_description = main_description._replace(
                    desc='\n' + main_description.desc.strip() + '\n' *
                         (1 if len(parsed) == 1 else 2))

        new_metadata = [main_description]
        for m in metadata:
            # Split newlines and remove leading and trailing whitespaces.
            stripped_desc = list(map(str.strip, m.desc.splitlines()))
            if len(stripped_desc) == 0:
                # Annotations should be on their own line, though no
                # further description follows.
                stripped_desc.append('')
            else:
                # Wrap parameter description onto next line if it follows
                # annotation directly.
                if stripped_desc[0] != '':
                    stripped_desc.insert(0, '')

            # Indent with 4 spaces.
            stripped_desc = ('' if line == '' else ' ' * indent_size
                             + line for line in stripped_desc)

            new_desc = '\n'.join(stripped_desc)

            # Strip away trailing whitespaces and obsolete newlines (except
            # one newline which is mandatory).
            new_desc = new_desc.rstrip() + '\n'

            new_metadata.append(m._replace(desc=new_desc.lstrip(' ')))
        return (new_metadata, warning_desc)

    def run(self, filename, file, language: str,
            docstyle: str='default', allow_missing_func_desc: str=False,
            indent_size: int=4, expand_one_liners: str=False):
        """
        Checks for certain in-code documentation styles.

        It currently checks for the following style: ::

            The first line needs to have no indentation.
                - Following lines can have indentation

            :param x:
                4 space indent
            :return:
                also 4 space indent
                following lines are also 4 space indented

        :param language: The programming language of the file(s).
        :param docstyle: The docstyle to use. For example ``default`` or
                         ``doxygen``. Docstyles are language dependent, meaning
                         not every language is supported by a certain docstyle.
        :param allow_missing_func_desc: When set ``True`` this will allow
                         functions with missing descriptions, allowing
                         functions to start with params.
        :param indent_size: Number of spaces per indentation level.
        :param expand_one_liners: When set ``True`` this will expand one liner
                         docstrings.
        """

        for doc_comment in self.extract(file, language, docstyle):
            parsed = doc_comment.parse()

            (new_metadata, warning_desc) = self.process_documentation(
                                parsed, allow_missing_func_desc, indent_size,
                                expand_one_liners)

            new_comment = DocumentationComment.from_metadata(
                new_metadata, doc_comment.docstyle_definition,
                doc_comment.marker, doc_comment.indent, doc_comment.position)

            if new_comment != doc_comment:
                # Something changed, let's apply a result.
                diff = self.generate_diff(file, doc_comment, new_comment)

                yield Result(
                    origin=self,
                    message=warning_desc,
                    affected_code=(diff.range(filename),),
                    diffs={filename: diff})