import argparse
import logging
import sys
 
 
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log", encoding="utf-8"),
        ],
    )
 
def cmd_import(args):
    from import_reviews import import_reviews
    import_reviews(args.file)
 
 
def cmd_run(args):
    from pipeline import run_pipeline_db
    run_pipeline_db(limit=args.limit)
 
 
def cmd_serve(args):
    try:
        import uvicorn
    except ImportError:
        print("Нужен uvicorn: pip install uvicorn fastapi")
        sys.exit(1)
    print(f"\n  Дашборд → http://localhost:{args.port}\n")
    uvicorn.run("api:app", host="0.0.0.0", port=args.port, reload=args.reload)
 
 
def cmd_entity(args):
    from entity_normalizer import normalize_entity
    result = normalize_entity(args.entity)
    print(f"\n  '{args.entity}'  →  '{result}'\n")
 
 
 
def build_parser():
    parser = argparse.ArgumentParser(description="REA AI — анализатор отзывов")
    parser.add_argument("--verbose", "-v", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
 
    p = sub.add_parser("import", help="Импортировать отзывы из JSON")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_import)
 
    p = sub.add_parser("run", help="Запустить пайплайн")
    p.add_argument("--limit", type=int, default=None)
    p.set_defaults(func=cmd_run)
 
    p = sub.add_parser("serve", help="Запустить дашборд")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    p.set_defaults(func=cmd_serve)
 
    p = sub.add_parser("entity", help="Проверить нормализацию entity")
    p.add_argument("entity", type=str)
    p.set_defaults(func=cmd_entity)
 
    return parser
 

 
if __name__ == "__main__":
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()
 
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nПрервано")
        sys.exit(0)
    except Exception as e:
        logging.getLogger(__name__).error("Ошибка: %s", e, exc_info=True)
        sys.exit(1)