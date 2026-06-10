import pytest
from config.week_keyboards import multi_week_keyboard, selected_week_names
from handlers.accountant import _build_department_report
from handlers.stats import _build_stats_message


def test_multi_week_keyboard_marks_selected():
    markup = multi_week_keyboard("acct:week", ["A", "B"], {1})
    texts = [btn.text for row in markup.inline_keyboard for btn in row]
    assert texts[0] == "A"
    assert texts[1] == "✅ B"
    assert "Показать отчёт" in texts


def test_selected_week_names():
    weeks = ["01.06–07.06", "08.06–14.06", "15.06–21.06"]
    assert selected_week_names(weeks, {0, 2}) == ["01.06–07.06", "15.06–21.06"]


@pytest.mark.asyncio
async def test_build_department_report_multiple_weeks(monkeypatch, sample_settings, sample_sheet_entries):
    async def fake_settings():
        return sample_settings
    async def fake_sheet_data(sheet):
        return sample_sheet_entries[sheet]
    monkeypatch.setattr("handlers.accountant.get_settings_cached", fake_settings)
    monkeypatch.setattr("handlers.accountant.get_sheet_data", fake_sheet_data)
    text = await _build_department_report(["08.06–14.06", "01.06–07.06"])
    assert text is not None
    assert "2 нед." in text
    assert "Аня Фролова" in text


@pytest.mark.asyncio
async def test_build_department_report_single_week(monkeypatch, sample_settings, sample_sheet_entries):
    async def fake_settings():
        return sample_settings
    async def fake_sheet_data(sheet):
        return sample_sheet_entries[sheet]
    monkeypatch.setattr("handlers.accountant.get_settings_cached", fake_settings)
    monkeypatch.setattr("handlers.accountant.get_sheet_data", fake_sheet_data)
    text = await _build_department_report(["08.06–14.06"])
    assert text is not None
    assert "неделя 08.06–14.06" in text


@pytest.mark.asyncio
async def test_build_department_report_empty_selection():
    assert await _build_department_report([]) is None


@pytest.mark.asyncio
async def test_build_stats_message_multiple_weeks(monkeypatch, sample_settings, sample_sheet_entries):
    async def fake_settings():
        return sample_settings
    async def fake_sheet_data(sheet):
        return sample_sheet_entries[sheet]
    monkeypatch.setattr("handlers.stats.get_settings_cached", fake_settings)
    monkeypatch.setattr("handlers.stats.get_sheet_data", fake_sheet_data)
    text = await _build_stats_message("Аня Фролова", ["08.06–14.06", "01.06–07.06"])
    assert text is not None
    assert "08.06–14.06" in text
    assert "01.06–07.06" in text
