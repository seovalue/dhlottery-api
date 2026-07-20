import json
import re
from typing import Dict, List

from rich.console import Console
from rich.table import Table

from dhapi.domain.lotto645_smart_picker import StrategyResult


class LotteryStdoutPrinter:
    def print_result_of_assign_virtual_account(self, 전용가상계좌, 결제신청금액):
        console = Console()

        console.print("✅ 가상계좌를 할당했습니다.")
        console.print("❗️입금 전 계좌주 이름을 꼭 확인하세요.")
        table = Table("전용가상계좌", "결제신청금액")
        table.add_row(전용가상계좌, 결제신청금액)

        console.print(table)

    def print_result_of_show_balance(self, *, 총예치금, 구매가능금액, 예약구매금액, 출금신청중금액, 구매불가능금액, 최근1달누적구매금액):
        console = Console()

        console.print("✅ 예치금 현황을 조회했습니다.")
        table = Table("총예치금", "구매가능금액", "예약구매금액", "출금신청중금액", "구매불가능금액", "최근1달누적구매금액")
        table.add_row(
            self._num_to_money_str(총예치금),
            self._num_to_money_str(구매가능금액),
            self._num_to_money_str(예약구매금액),
            self._num_to_money_str(출금신청중금액),
            self._num_to_money_str(구매불가능금액),
            self._num_to_money_str(최근1달누적구매금액),
        )
        console.print(table)
        console.print("[dim](구매불가능금액 = 예약구매금액 + 출금신청중금액)[/dim]")

    def _num_to_money_str(self, num):
        return f"{num:,} 원"

    def print_result_of_buy_lotto645(self, slots: List[Dict]):
        """
        :param slots: [{"slot": "A", "mode": "자동", "numbers": [1, 2, 3, 4, 5, 6]}, ...]
        :return:
        """
        console = Console()

        console.print("✅ 로또6/45 복권을 구매했습니다.")
        table = Table("슬롯", "Mode", "번호1", "번호2", "번호3", "번호4", "번호5", "번호6")
        for slot in slots:
            table.add_row(slot["slot"], slot["mode"], *slot["numbers"])
        console.print(table)

    def print_result_of_show_buy_list(self, data: List[Dict], output_format: str, start_date: str, end_date: str):
        console = Console()

        if output_format == "json":
            json_results = self._build_json_results(data)
            print(json.dumps(json_results, ensure_ascii=False, indent=2))
            return

        console.print(f"✅ 구매 내역을 조회했습니다. ({start_date} ~ {end_date})")

        if not data:
            console.print("구매 내역이 없습니다.")
            return

        for table_data in data:
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])

            if not headers:
                continue

            if len(rows) == 1 and len(rows[0]) == 1 and "조회 결과가 없습니다" in rows[0][0]:
                console.print(f"[dim]{rows[0][0]}[/dim]\n")
                continue

            table = Table(*headers)
            for row in rows:
                padded_row = self._pad_row(row, len(headers))
                table.add_row(*padded_row)

            console.print(table)
            console.print("\n")

    def _build_json_results(self, data: List[Dict]) -> List[Dict]:
        json_results = []
        for table_data in data:
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])

            if not headers:
                continue

            for row in rows:
                item = self._parse_row_for_json(row, headers)
                json_results.append(item)
        return json_results

    def _parse_row_for_json(self, row: List[str], headers: List[str]) -> Dict:
        item = {}
        for i, header in enumerate(headers):
            if i < len(row):
                if header == "선택번호/복권번호":
                    parsed_numbers = self._parse_lotto_numbers(row[i])
                    if parsed_numbers:
                        item["numbers"] = parsed_numbers
                    else:
                        item[header] = row[i]
                else:
                    item[header] = row[i]
        return item

    def _parse_lotto_numbers(self, value: str) -> List[Dict]:
        parsed_numbers = []
        for line in value.split("\n"):
            line = line.strip()
            if not line:
                continue

            match = re.search(r"\[([A-E])\]\s*([^:]+):\s*([\d\s]+)", line)
            if match:
                slot = match.group(1)
                mode = match.group(2).strip()
                nums_str = match.group(3).strip()
                nums = [int(n) for n in nums_str.split()]
                parsed_numbers.append(
                    {
                        "slot": slot,
                        "mode": mode,
                        "numbers": nums,
                    }
                )
        return parsed_numbers

    def print_result_of_suggest_lotto645(
        self,
        strategies: List[StrategyResult],
        last_round: int,
        freq_all: Dict[int, int],
        freq_recent: Dict[int, int],
        recent_rounds: int,
    ):
        console = Console()
        console.print(f"\n[bold cyan]✨ 로또6/45 스마트 번호 추천[/bold cyan] [dim](1~{last_round}회 통계 기반)[/dim]\n")

        avg_all = sum(freq_all.values()) / 45
        console.print("[bold]📊 역대 TOP5 번호[/bold]", end="  ")
        top5 = sorted(freq_all, key=lambda n: freq_all[n], reverse=True)[:5]
        console.print(" ".join(f"[green]{n}[/green]({freq_all[n]}회)" for n in top5))

        console.print(f"[bold]🔥 최근 {recent_rounds}회 TOP5 번호[/bold]", end="  ")
        recent_top5 = sorted(freq_recent, key=lambda n: freq_recent[n], reverse=True)[:5]
        console.print(" ".join(f"[yellow]{n}[/yellow]({freq_recent[n]}회)" for n in recent_top5))

        console.print(f"[bold]❄️  최근 {recent_rounds}회 BOTTOM5 번호[/bold]", end="  ")
        recent_bot5 = sorted(freq_recent, key=lambda n: freq_recent[n])[:5]
        console.print(" ".join(f"[blue]{n}[/blue]({freq_recent[n]}회)" for n in recent_bot5))
        console.print()

        table = Table("전략", "설명", "추천 번호", "합계", "홀/짝")
        for s in strategies:
            nums_str = "  ".join(f"{n:2d}" for n in s.numbers)
            total = sum(s.numbers)
            odd_cnt = sum(1 for n in s.numbers if n % 2 == 1)
            table.add_row(
                f"[bold]{s.label}[/bold]",
                f"[dim]{s.description}[/dim]",
                nums_str,
                str(total),
                f"{odd_cnt}홀/{6 - odd_cnt}짝",
            )
        console.print(table)
        console.print()
        console.print("[dim]💡 위 번호를 구매하려면: dhapi buy-lotto645 '번호1,번호2,...'[/dim]")

    def _pad_row(self, row: List[str], target_length: int) -> List[str]:
        if len(row) == target_length:
            return row
        elif len(row) < target_length:
            return row + [""] * (target_length - len(row))
        else:
            return row[:target_length]
