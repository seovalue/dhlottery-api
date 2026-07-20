from typing import Annotated, Optional, List

import typer
from rich.console import Console
from rich.table import Table

from dhapi.config.logger import set_logger
from dhapi.domain.deposit import Deposit
from dhapi.domain.lotto645_smart_picker import Lotto645SmartPicker
from dhapi.domain.lotto645_ticket import Lotto645Ticket
from dhapi.port.credentials_provider import CredentialsProvider
from dhapi.router.dependency_factory import build_lottery_client, build_lotto645_stats_fetcher, build_lottery_endpoint, build_version_provider, build_lotto645_buy_confirmer

app = typer.Typer(
    help="동행복권 비공식 API\n\n각 명령어에 대한 자세한 도움말은 'dhapi [명령어] -h'를 입력하세요.",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=False,
    add_completion=False,
)


def logger_callback(is_debug: bool):
    app.pretty_exceptions_enable = is_debug
    set_logger(is_debug)


def version_callback(show_version: Optional[bool]):
    if show_version:
        version_provider = build_version_provider()
        version_provider.show_version()
        raise typer.Exit()


@app.command(
    help="""
예치금 충전용 가상계좌를 세팅합니다.

dhapi에서는 본인 전용 계좌를 발급받는 것까지만 가능합니다. 출력되는 계좌로 직접 입금해주세요.
""",
)
def assign_virtual_account(
    amount: Annotated[
        int, typer.Argument(help="입금할 금액을 지정합니다 (5천원, 1만원, 2만원, 3만원, 5만원, 10만원, 20만원, 30만원, 50만원, 70만원, 100만원 중 하나)", metavar="amount")
    ] = 50000,
    profile: Annotated[str, typer.Option("-p", "--profile", help="프로필을 지정합니다", metavar="")] = "default",
    _debug: Annotated[bool, typer.Option("-d", "--debug", help="debug 로그를 활성화합니다.", callback=logger_callback)] = False,
):
    user = CredentialsProvider(profile).get_user()
    deposit = Deposit(amount)

    client = build_lottery_client(user)
    client.assign_virtual_account(deposit)


@app.command(help="""
예치금 현황을 조회합니다.
""")
def show_balance(
    profile: Annotated[str, typer.Option("-p", "--profile", help="프로필을 지정합니다", metavar="")] = "default",
    _debug: Annotated[bool, typer.Option("-d", "--debug", help="debug 로그를 활성화합니다.", callback=logger_callback)] = False,
):
    user = CredentialsProvider(profile).get_user()

    client = build_lottery_client(user)
    client.show_balance()


@app.command(help="""
구매 내역을 조회합니다.

기본적으로 최근 14일간의 내역을 조회하며, --start-date 및 --end-date 옵션을 통해 조회 기간을 지정할 수 있습니다.
""")
def show_buy_list(
    profile: Annotated[str, typer.Option("-p", "--profile", help="프로필을 지정합니다", metavar="")] = "default",
    output_format: Annotated[str, typer.Option("-f", "--format", help="출력 형식을 지정합니다 (table, json).")] = "table",
    start_date: Annotated[Optional[str], typer.Option("-s", "--start-date", help="조회 시작 날짜 (YYYYMMDD)")] = None,
    end_date: Annotated[Optional[str], typer.Option("-e", "--end-date", help="조회 종료 날짜 (YYYYMMDD)")] = None,
    _debug: Annotated[bool, typer.Option("-d", "--debug", help="debug 로그를 활성화합니다.", callback=logger_callback)] = False,
):
    user = CredentialsProvider(profile).get_user()
    client = build_lottery_client(user)
    client.show_buy_list(output_format, start_date, end_date)


@app.command(
    help="""등록된 프로필 목록을 출력합니다.""",
)
def show_profiles():
    try:
        profiles = CredentialsProvider.list_profiles()
    except FileNotFoundError as e:
        print(f"❌ {e.args[0]}")
        raise typer.Exit(code=1)

    console = Console()
    table = Table("profiles")
    for name in profiles:
        table.add_row(name)

    console.print(table)


@app.command(help="""
로또6/45 복권을 구매합니다.

매주 최대 다섯 장까지 구매할 수 있습니다 (5 tickets).

[예시]

dhapi buy-lotto645 : 자동모드 5장 (default)

dhapi buy-lotto645 '' : 자동모드 1장

dhapi buy-lotto645 '1,2,3,4,5,6' : 수동모드 1장 (고정번호: 1,2,3,4,5,6)

dhapi buy-lotto645 '1,2,3' : 반자동모드 1장 (고정번호: 1,2,3)

dhapi buy-lotto645 '1,2,3,4,5,6' '7,8,9' : 수동모드 1장 (고정번호: 1,2,3,4,5,6), 반자동모드 1장 (고정번호: 7,8,9)

dhapi buy-lotto645 '' '' '' '1' : 자동모드 3장, 반자동모드 1장 (고정번호: 1)
""")
def buy_lotto645(
    tickets: Annotated[List[str], typer.Argument(help="구매할 번호를 입력합니다. 생략 시 자동모드로 5장 구매합니다.", metavar="tickets", show_default=False)] = None,
    always_yes: Annotated[bool, typer.Option("-y", "--yes", help="구매 전 확인 절차를 스킵합니다.")] = False,
    profile: Annotated[str, typer.Option("-p", "--profile", help="프로필을 지정합니다", metavar="")] = "default",
    _debug: Annotated[bool, typer.Option("-d", "--debug", help="debug 로그를 활성화합니다.", callback=logger_callback)] = False,
):
    cred = CredentialsProvider(profile)
    user = cred.get_user()
    tickets = Lotto645Ticket.create_tickets(tickets) if tickets else Lotto645Ticket.create_auto_tickets(count=5)

    client = build_lottery_client(user)
    confirmer = build_lotto645_buy_confirmer()

    ok = confirmer.confirm(tickets, always_yes)
    if not ok:
        raise typer.Exit()

    client.buy_lotto645(tickets)


@app.command(help="""
역대 당첨 통계를 분석해 우리만의 룰로 로또6/45 번호를 추천합니다.

5가지 전략으로 각 1세트씩 추천합니다:

  hot_cold      최근 핫넘버 3 + 역대 콜드넘버 2 + 랜덤 1

  zone_balance  5구간에서 각 1개 + 핫 구간 1개 추가

  contrarian    역대 多인데 최근 少(때가 됐다) 3 + 역대 少인데 최근 多(흐름탑승) 3

  balanced      홀수 3개 + 짝수 3개 (합계 100~175 보장)

  our_formula   역대TOP2 + 최근TOP2 + 역대하위1(반전카드) + 랜덤1
""")
def suggest_lotto645(
    recent: Annotated[int, typer.Option("-r", "--recent", help="최근 N회 기준으로 핫/콜드 분석 (기본값: 50)")] = 50,
    _debug: Annotated[bool, typer.Option("-d", "--debug", help="debug 로그를 활성화합니다.", callback=logger_callback)] = False,
):
    try:
        fetcher = build_lotto645_stats_fetcher()
        last_round = fetcher.fetch_last_round()
        freq_all = fetcher.fetch_no_stats()
        start_epsd = max(1, last_round - recent + 1)
        freq_recent = fetcher.fetch_no_stats(start_epsd=str(start_epsd), end_epsd=str(last_round))
    except Exception as e:
        raise RuntimeError(f"❗ 통계 데이터를 가져오지 못했습니다: {e}")

    picker = Lotto645SmartPicker(freq_all, freq_recent, last_round)
    strategies = picker.pick_all()

    endpoint = build_lottery_endpoint()
    endpoint.print_result_of_suggest_lotto645(
        strategies=strategies,
        last_round=last_round,
        freq_all=freq_all,
        freq_recent=freq_recent,
        recent_rounds=recent,
    )


@app.command(help="""
dhapi 버전을 출력합니다.
""")
def version():
    version_callback(True)


def entrypoint():
    app()
