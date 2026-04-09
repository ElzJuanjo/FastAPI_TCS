from src.infra.adapters.person_repository import PersonRepositorySQL


class PersonUseCases:
    def __init__(self):
        self.repo = PersonRepositorySQL()

    def find_by_document(self, nit: str) -> dict:
        return self.repo.find_by_document(nit)
