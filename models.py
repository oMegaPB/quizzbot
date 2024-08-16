from __future__ import annotations

import json
import pathlib

from attrs import frozen

@frozen
class Config:
    team_name: str
    token: str
    questions: dict
    owner_accepter_id: int
    work_chat_url: str

    @classmethod
    def from_file(cls, filename: str) -> Config:
        cwd = pathlib.Path(__file__).parent
        file = cwd.joinpath(filename).open("r", encoding="u8")
        return cls(**json.load(file))