from hippy.lexer import Token, Lexer
from hippy.sourceparser import SourceParser, LexerWrapper, ParseError, get_lexer
from hippy.astcompiler import compile_ast

from rpython.rlib.objectmodel import we_are_translated

MODE_LITERAL = 0
MODE_EQUALSIGN = 1
MODE_PHPCODE = 2


class PHPLexerWrapper(LexerWrapper):
    def __init__(self, source, filename="", interp=None):
        self.lexer = get_lexer(we_are_translated())
        self.source = source
        self.startlineno = 1
        self.startindex = 0
        self.mode = MODE_LITERAL
        self.filename = filename
        self.heredoc_term = None
        self.interp = interp

    def next(self):
        mode = self.mode
        if mode == MODE_PHPCODE:
            return self.next_phpcode()
        elif mode == MODE_LITERAL:
            return self.next_literal_mode()
        elif mode == MODE_EQUALSIGN:
            return self.next_equal_sign()
        else:
            assert 0

    def next_literal_mode(self):
        # "literal" mode, i.e. outside "<?php ?>" tags: generates
        # one B_LITERAL_BLOCK until the next opening "<?php" tag
        self.mode = MODE_PHPCODE
        source = self.source
        index = self.startindex
        assert index >= 0
        tagindex = source.find('<?', index)
        if tagindex == -1:
            tagindex = len(source)
        assert tagindex >= 0
        startindex = self.startindex
        assert startindex >= 0
        block_of_text = source[startindex:tagindex]   # may be empty
        tok = Token('B_LITERAL_BLOCK', block_of_text, self.startlineno)
        self.startlineno += block_of_text.count('\n')
        if source[tagindex:tagindex+5].lower() == '<?php':
            pos = tagindex + 5
        elif source[tagindex:tagindex+3] == '<?=':
            pos = tagindex + 3
            self.mode = MODE_EQUALSIGN
        else:
            pos = tagindex + 2
        self.lexer.input(self.source, pos, self.startlineno)
        return tok

    def next_equal_sign(self):
        self.mode = MODE_PHPCODE
        return Token("T_ECHO", "echo", self.startlineno)

    def next_phpcode(self):
        while 1:
            tok = self.lexer.token()
            if tok is None:
                return None       # end of file
            elif tok.name == 'H_NEW_LINE':
                continue          # ignore these and continue
            elif tok.name == 'H_TABULATURE':
                continue          # ignore these and continue
            elif tok.name == 'H_WHITESPACE':
                continue          # ignore these and continue
            elif tok.name == 'T_COMMENT':
                # look for "?>" inside single-line comments too
                if not tok.value.startswith('/*'):
                    i = tok.value.find('?>')
                    if i >= 0:
                        endpos = self.lexer.pos - len(tok.value) + i + 2
                        return self.end_current_block(tok, endpos)
                continue
            elif tok.name == 'B_END_OF_CODE_BLOCK':
                return self.end_current_block(tok, self.lexer.pos)
            elif tok.name == 'T_HALT_COMPILER':
                return self.do_halt_compiler()
            else:
                return tok        # a normal php token

    def end_current_block(self, tok, endpos):
        # a "?>" marker that ends the current block of code
        # generates a ";" token followed by a B_LITERAL_BLOCK
        self.startlineno = tok.getsourcepos()
        self.startindex = endpos
        self.mode = MODE_LITERAL
        if (self.startindex < len(self.source) and
                self.source[self.startindex] == '\n'):
            self.startlineno += 1     # consume \n if immediately following
            self.startindex += 1
        return Token(";", ";", tok.getsourcepos())

    def do_halt_compiler(self):
        for expecting in ['(', ')', ';']:
            token = self.next()
            if token is None or token.name != expecting:
                raise ParseError('"__halt_compiler" not followed by "();"',
                                 token.getsourcepos())
        #
        # hack: copies the end position to a constant
        if self.interp is not None:
            if '__COMPILER_HALT_OFFSET__' not in self.interp.constants:
                if self.mode == MODE_LITERAL:
                    endpos = self.startindex
                else:
                    endpos = self.lexer.pos
                w_end = self.interp.space.newint(endpos)
                self.interp.constants['__COMPILER_HALT_OFFSET__'] = w_end
        #
        return None

DEBUG = False


def compile_php(filename, source, space, interp=None):
    """Parse and compile a PHP file, starting in literal mode (i.e.
    dumping all input directly) until the first '<?' or '<?php'.
    Supports a mixture of blocks of code between the blocks of texts."""

    phplexerwrapper = PHPLexerWrapper(source, filename, interp)
    if DEBUG:
        lst = []
        while True:
            tok = phplexerwrapper.next()
            if tok is None:
                break
            else:
                lst.append(tok)
        print [x.__dict__ for x in lst]
        phplexerwrapper = iter(lst + [None])
    parser = SourceParser(space, None, filename=filename)
    tokens = parser.parser.parse(phplexerwrapper, state=parser)
    bc = compile_ast(filename, source, tokens, space)
    return bc
