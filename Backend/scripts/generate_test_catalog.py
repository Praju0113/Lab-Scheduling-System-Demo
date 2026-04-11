from app.catalog import build_test_catalog

if __name__ == '__main__':
    print(f'Loaded {len(build_test_catalog())} tests from JSON catalog')
