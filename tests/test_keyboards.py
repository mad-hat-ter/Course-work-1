from config.keyboards import inline_from_items, main_menu_keyboard


def test_main_menu_curator():
    keyboard = main_menu_keyboard("curator")
    texts = [button.text for row in keyboard.keyboard for button in row]
    assert "Просмотр свободных смен" in texts
    assert "Мой график и статистика" in texts
    assert "Главное меню" in texts
    assert "Добавить расписание" not in texts


def test_main_menu_admin_has_add_schedule():
    keyboard = main_menu_keyboard("admin")
    texts = [button.text for row in keyboard.keyboard for button in row]
    assert "Добавить расписание" in texts


def test_main_menu_accountant():
    keyboard = main_menu_keyboard("accountant")
    texts = [button.text for row in keyboard.keyboard for button in row]
    assert "Просмотр статистики отдела" in texts
    assert "Главное меню" in texts


def test_main_menu_unknown_role_fallback():
    keyboard = main_menu_keyboard("guest")
    texts = [button.text for row in keyboard.keyboard for button in row]
    assert texts == ["Главное меню"]


def test_multi_week_keyboard_has_back():
    from config.week_keyboards import multi_week_keyboard

    markup = multi_week_keyboard("stats:week", ["A"], set())
    callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert "nav:back" in callbacks


def test_inline_from_items_callback_data():
    markup = inline_from_items("stats:sheet", [("A", "a"), ("B", "b")], back=False)
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]
    assert callbacks == ["stats:sheet:0", "stats:sheet:1"]


def test_inline_from_items_with_back():
    markup = inline_from_items("book:week", [("W", "w")], back=True)
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]
    assert callbacks == ["book:week:0", "nav:back"]
