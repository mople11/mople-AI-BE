from django.core.paginator import EmptyPage, Paginator


def paginate_queryset(queryset, *, page: int, page_size: int) -> tuple[list, dict]:
    if page_size < 1:
        raise ValueError("page_size는 1 이상이어야 합니다.")

    paginator = Paginator(queryset, page_size)
    try:
        items = list(paginator.page(page))
    except EmptyPage:
        items = []
    return items, {
        "page": page,
        "pageSize": page_size,
        "totalCount": paginator.count,
        "totalPages": paginator.num_pages if paginator.count else 0,
    }
