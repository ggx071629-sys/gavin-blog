from typing import Annotated

from fastapi import Query

PageLimit = Annotated[int, Query(ge=1, le=100)]
SearchLimit = Annotated[int, Query(ge=1, le=50)]
PageOffset = Annotated[int, Query(ge=0, le=100_000)]
