from films import list_films


def test_list_100_films_with_actors_and_categories(session, assert_max_queries):
    with assert_max_queries(3):
        films = list_films(session)
    assert len(films) == 100
    assert all(f["actors"] for f in films)
    assert all(f["categories"] for f in films)
