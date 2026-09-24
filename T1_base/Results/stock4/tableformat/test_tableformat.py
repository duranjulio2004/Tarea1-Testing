import pytest
from io import StringIO
from contextlib import redirect_stdout
from tableformat import (
    print_table, TableFormatter, TextTableFormatter, 
    CSVTableFormatter, HTMLTableFormatter, ColumnFormatMixin, 
    UpperHeadersMixin, create_formatter
)

class MockRecord:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

def test_print_table_validation():
    with pytest.raises(RuntimeError, match='Expected a TableFormatter'):
        print_table([], [], None)

def test_print_table_logic():
    class TestFormatter(TableFormatter):
        def __init__(self):
            self.calls = []
        def headings(self, headers):
            self.calls.append(('headings', headers))
        def row(self, rowdata):
            self.calls.append(('row', rowdata))
    
    formatter = TestFormatter()
    records = [MockRecord(a=1, b=2), MockRecord(a=3, b=4)]
    print_table(records, ['a', 'b'], formatter)
    
    assert formatter.calls == [
        ('headings', ['a', 'b']),
        ('row', [1, 2]),
        ('row', [3, 4])
    ]

def test_formatters_output():
    records = [MockRecord(a=10, b=20)]
    fields = ['a', 'b']
    
    # Text
    f = TextTableFormatter()
    with redirect_stdout(StringIO()) as out:
        print_table(records, fields, f)
        assert "        10         20" in out.getvalue()
        
    # CSV
    f = CSVTableFormatter()
    with redirect_stdout(StringIO()) as out:
        print_table(records, fields, f)
        assert "a,b\n10,20\n" in out.getvalue()
        
    # HTML
    f = HTMLTableFormatter()
    with redirect_stdout(StringIO()) as out:
        print_table(records, fields, f)
        res = out.getvalue()
        assert "<tr> <th>a</th> <th>b</th> </tr>" in res
        assert "<tr> <td>10</td> <td>20</td> </tr>" in res

def test_mixins():
    class Derived(ColumnFormatMixin, TextTableFormatter):
        formats = ['%0.2f', '%d']
    
    f = Derived()
    with redirect_stdout(StringIO()) as out:
        f.row([1.234, 10])
        # TextTableFormatter prints 10 spaces, mixed with fmt
        assert "      1.23         10" in out.getvalue()

    class UpperDerived(UpperHeadersMixin, TextTableFormatter):
        pass
    
    f = UpperDerived()
    with redirect_stdout(StringIO()) as out:
        f.headings(['a', 'b'])
        assert "         A          B" in out.getvalue()

def test_create_formatter():
    # Test valid creations
    f_text = create_formatter('text')
    assert isinstance(f_text, TextTableFormatter)
    
    f_csv = create_formatter('csv', column_formats=['%s'])
    assert isinstance(f_csv, CSVTableFormatter)
    
    f_html = create_formatter('html', upper_headers=True)
    assert isinstance(f_html, HTMLTableFormatter)
    
    # Test invalid format
    with pytest.raises(RuntimeError, match='Unknown format'):
        create_formatter('xml')

def test_empty_records():
    class TestFormatter(TableFormatter):
        def headings(self, h): pass
        def row(self, r): pass
    
    formatter = TestFormatter()
    # Should not raise, loop just won't execute
    print_table([], ['f1'], formatter)

def test_column_format_mixin_integration():
    # Test path where rowdata is empty
    class Custom(ColumnFormatMixin, CSVTableFormatter):
        formats = []
    
    f = Custom()
    with redirect_stdout(StringIO()):
        f.row([]) # zip([]) results in empty list
