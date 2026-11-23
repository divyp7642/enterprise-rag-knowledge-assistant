
from app.db.database import SessionLocal
from app.rag.answer_generator import RAGAnswerService


def main():
    db = SessionLocal()

    try:
        rag_service = RAGAnswerService()

        question = (
            "What could have gone better "
            "during LMU Unified Sprint 4?"
        )

        result = rag_service.generate_answer(
            db=db,
            question=question,
            top_k=3
        )

        print("\nQUESTION:")
        print(result["question"])

        print("\nAI GENERATED ANSWER:")
        print(result["answer"])

        print("\nRETRIEVED SOURCES:")
        for source in result["sources"]:
            print(source)

    finally:
        db.close()


if __name__ == "__main__":
    main()
