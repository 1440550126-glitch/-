"""古典名著测试。可直接运行：python tests/test_classic_books.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dsoul.classic_books import (  # noqa: E402
    about,
    books,
    characters,
    find_book,
    four_classics,
    is_book_query,
)


def test_books_and_four():
    bs = books()
    for b in ("红楼梦", "西游记", "水浒传", "三国演义"):
        assert b in bs
    fc = four_classics()
    assert "红楼梦" in fc and "三国演义" in fc


def test_about():
    assert "曹雪芹" in about("红楼梦")
    assert "取经" in about("西游记")
    assert about("查无此书") == ""


def test_characters():
    assert "孙悟空" in characters("西游记")
    assert "诸葛亮" in characters("三国演义")


def test_find_book_alias():
    assert find_book("石头记讲什么") == "红楼梦"
    assert find_book("水浒主要人物") == "水浒传"
    assert find_book("今天天气") == ""


def test_about_from_sentence():
    assert "施耐庵" in about("水浒传谁写的")


def test_is_book_query():
    assert is_book_query("四大名著是哪四部")
    assert is_book_query("西游记主要人物有谁")
    assert is_book_query("红楼梦谁写的")
    assert not is_book_query("今天几号")
    assert not is_book_query("我在看三国")             # 没问作者/人物/内容


if __name__ == "__main__":
    for _n, _f in sorted(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print("PASS", _n)
    print("✅ classic_books: all tests passed")
