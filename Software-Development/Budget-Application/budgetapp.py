from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.factory import Factory
from kivy.properties import ListProperty, NumericProperty, StringProperty, BooleanProperty
from kivy.clock import Clock
import json, os, binascii, hashlib, hmac, time

DATA_FILE = "data/transactions.json"
SAVINGS_FILE = "data/savings.json"
BILLS_FILE = "data/bills.json"
SETTINGS_FILE = "data/settings.json"


class Dashboard(Screen):
    total_income = NumericProperty(0)
    total_expenses = NumericProperty(0)
    balance = NumericProperty(0)
    total_saved = NumericProperty(0)
    total_target = NumericProperty(0)
    progress_percent = NumericProperty(0)
    budget_total = NumericProperty(0)
    budget_spent = NumericProperty(0)
    budget_remaining = NumericProperty(0)
    budget_month = StringProperty("")
    formatted_budget_total = StringProperty("")
    formatted_budget_spent = StringProperty("")
    formatted_budget_remaining = StringProperty("")
    budget_percent = NumericProperty(0)
    formatted_income = StringProperty("")
    formatted_expenses = StringProperty("")
    formatted_balance = StringProperty("")

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        transactions = app.transactions
        income = sum(t["amount"] for t in transactions if t["amount"] > 0)
        expenses = sum(abs(t["amount"]) for t in transactions if t["amount"] < 0)
        self.total_income = income
        self.total_expenses = expenses
        self.balance = income - expenses
        self.formatted_income = app.format_money(self.total_income)
        self.formatted_expenses = app.format_money(self.total_expenses)
        self.formatted_balance = app.format_money(self.balance)
        self.total_saved = sum(g.get("current", 0) for g in app.savings_goals if not g.get("completed", False))
        self.total_target = sum(g.get("target", 0) for g in app.savings_goals if not g.get("completed", False))
        if self.total_target > 0:
            self.progress_percent = (self.total_saved / self.total_target) * 100
        else:
            self.progress_percent = 0
        if hasattr(app, "active_budget"):
            b = app.active_budget
            self.budget_total = b.get("total_budget", 0)
            self.budget_spent = b.get("spent", 0)
            self.budget_remaining = b.get("remaining", 0)
            try:
                self.budget_month = b.get("month", time.strftime("%B"))
            except Exception:
                self.budget_month = time.strftime("%B")
            self.formatted_budget_total = app.format_money(self.budget_total)
            self.formatted_budget_spent = app.format_money(self.budget_spent)
            self.formatted_budget_remaining = app.format_money(self.budget_remaining)
            if self.budget_total > 0:
                self.budget_percent = (self.budget_spent / self.budget_total) * 100
            else:
                self.budget_percent = 0
        else:
            self.budget_total = 0
            self.budget_spent = 0
            self.budget_remaining = 0
            self.budget_percent = 0
            self.budget_month = time.strftime("%B")
            self.formatted_budget_total = app.format_money(0)
            self.formatted_budget_spent = app.format_money(0)
            self.formatted_budget_remaining = app.format_money(0)



class LoginScreen(Screen):
    def on_pre_enter(self, *args):
        app = App.get_running_app()
        if not app.pin_hash:
            Clock.schedule_once(lambda dt: setattr(self.manager, "current", "setup_account"), 0)

    def login(self):
        app = App.get_running_app()
        pin = self.ids.pin_input.text
        if app.pin_hash and app.pin_salt and app._verify_pin(pin, app.pin_salt, app.pin_hash):
            self.ids.pin_input.text = ""
            self.ids.error_label.text = ""
            self.manager.current = "dashboard"
        else:
            self.ids.error_label.text = "Incorrect PIN"

    def go_to_setup(self):
        self.manager.current = "setup_account"


class SetupAccount(Screen):
    def create_account(self):
        app = App.get_running_app()
        pin1 = self.ids.new_pin_input.text.strip()
        pin2 = self.ids.confirm_pin_input.text.strip()
        if not pin1 or not pin2:
            self.ids.error_label.text = "Enter PIN in both fields"
            return
        if not pin1.isdigit() or not pin2.isdigit():
            self.ids.error_label.text = "PIN must be numeric"
            return
        if len(pin1) < 4:
            self.ids.error_label.text = "PIN must be at least 4 digits"
            return
        if pin1 != pin2:
            self.ids.error_label.text = "PINs do not match"
            return
        salt_hex, hash_hex = app._hash_pin(pin1)
        app.pin_salt = salt_hex
        app.pin_hash = hash_hex
        app.save_settings()
        self.ids.new_pin_input.text = ""
        self.ids.confirm_pin_input.text = ""
        self.ids.error_label.text = "Account created — please login"
        self.manager.current = "login"


class Settings(Screen):
    def on_pre_enter(self, *args):
        app = App.get_running_app()
        if "font_slider" in self.ids:
            self.ids.font_slider.value = app.font_size
        if "name_input" in self.ids:
            self.ids.name_input.text = app.user_name
        if "email_input" in self.ids:
            self.ids.email_input.text = app.user_email
        if "theme_spinner" in self.ids:
            self.ids.theme_spinner.text = app.theme
        if "currency_spinner" in self.ids:
            self.ids.currency_spinner.text = app.currency
        if "new_pin_input" in self.ids:
            self.ids.new_pin_input.text = ""
        if "confirm_pin_input" in self.ids:
            self.ids.confirm_pin_input.text = ""

    def save_settings_screen(self):
        app = App.get_running_app()
        if "font_slider" in self.ids:
            app.font_size = int(self.ids.font_slider.value)
        if "name_input" in self.ids:
            app.user_name = self.ids.name_input.text
        if "email_input" in self.ids:
            app.user_email = self.ids.email_input.text
        if "theme_spinner" in self.ids:
            theme_text = self.ids.theme_spinner.text or app.theme
            app.set_theme(theme_text)
        if "currency_spinner" in self.ids:
            app.currency = self.ids.currency_spinner.text or app.currency
        if "new_pin_input" in self.ids and "confirm_pin_input" in self.ids:
            new_pin = self.ids.new_pin_input.text.strip()
            confirm_pin = self.ids.confirm_pin_input.text.strip()
            if new_pin and new_pin == confirm_pin and new_pin.isdigit() and len(new_pin) >= 4:
                salt_hex, hash_hex = app._hash_pin(new_pin)
                app.pin_salt = salt_hex
                app.pin_hash = hash_hex
        app.save_settings()
        try:
            app.root.get_screen("dashboard").on_pre_enter()
        except Exception:
            pass
        try:
            app.root.get_screen("view_savings_goals").on_pre_enter()
        except Exception:
            pass
        try:
            app.root.get_screen("view_transactions").on_pre_enter()
        except Exception:
            pass
        self.manager.current = "dashboard"


class AddTransaction(Screen):
    def add(self):
        app = App.get_running_app()
        try:
            amount = float(self.ids.amount_input.text)
        except Exception:
            amount = 0.0
        category = self.ids.category_input.text
        new_transaction = {"amount": amount, "category": category}
        app.transactions.append(new_transaction)
        app.save_data()
        self.ids.amount_input.text = ""
        self.ids.category_input.text = ""
        self.manager.current = "dashboard"


class ViewTransactions(Screen):
    def on_pre_enter(self, *args):
        app = App.get_running_app()
        self.ids.transactions_list.clear_widgets()
        for t in app.transactions:
            text = f"{t['category']}: {app.format_money(t['amount'])}"
            self.ids.transactions_list.add_widget(TransactionItem(text=text))


class ViewSavingsGoals(Screen):
    def on_pre_enter(self, *args):
        self.refresh_list()

    def refresh_list(self):
        app = App.get_running_app()
        grid = self.ids.goals_list
        grid.clear_widgets()
        print('[debug] ViewSavingsGoals.refresh_list — total goals in model =', len(app.savings_goals))
        seen = set()
        for index, g in enumerate(app.savings_goals):
            if g.get("completed", False):
                continue
            name = str(g.get('name', '')).strip()
            try:
                tval = float(g.get('target', 0) or 0)
            except Exception:
                tval = 0
            try:
                cval = float(g.get('current', 0) or 0)
            except Exception:
                cval = 0
            if not name and tval == 0 and cval == 0 and not str(g.get('deadline', '')).strip():
                continue
            key = (name, float(tval), float(cval), str(g.get('deadline', '')).strip())
            if key in seen:
                print(f"[debug] skipping duplicate goal at index={index} name='{name}'")
                continue
            seen.add(key)
            print(f"[debug] rendering goal index={index} name='{name}' target={tval} current={cval} deadline='{g.get('deadline','')}'")
            try:
                t = float(g.get("target", 0) or 0)
                c = float(g.get("current", 0) or 0)
                pct = (c / t) * 100 if t > 0 else 0
            except Exception:
                pct = 0
            item = SavingsGoalItem(
                goal_index=index,
                name=str(g.get("name", "")),
                target=str(g.get("target", "")),
                current=str(g.get("current", "")),
                deadline=str(g.get("deadline", "")),
                progress=pct,
            )
            grid.add_widget(item)


class AddSavingsGoal(Screen):
    def add_goal(self):
        app = App.get_running_app()
        try:
            target = float(self.ids.target_input.text or "0")
        except Exception:
            target = 0.0
        try:
            current = float(self.ids.current_input.text or "0")
        except Exception:
            current = 0.0
        name = (self.ids.name_input.text or '').strip()
        if not name:
            if hasattr(self.ids, 'error_label'):
                self.ids.error_label.text = 'Please enter a name for the goal'
            return
        deadline = self.ids.deadline_input.text
        new_goal = {
            "name": name,
            "target": target,
            "current": current,
            "deadline": deadline,
            "completed": False,
        }
        try:
            key = (str(new_goal["name"]).strip(), float(new_goal["target"]), float(new_goal["current"]), str(new_goal["deadline"]).strip())
            exists = False
            for g in app.savings_goals:
                try:
                    k = (str(g.get("name", "")).strip(), float(g.get("target", 0) or 0), float(g.get("current", 0) or 0), str(g.get("deadline", "")).strip())
                except Exception:
                    continue
                if k == key:
                    exists = True
                    break
            if exists:
                if hasattr(self.ids, 'error_label'):
                    self.ids.error_label.text = 'Goal already exists'
                self.manager.current = 'view_savings_goals'
                return
        except Exception:
            pass
        app.savings_goals.append(new_goal)
        try:
            app.save_data()
        except Exception:
            app.show_try_again_popup("Failed to save new goal", lambda: self.add_goal())
            return
        self.ids.name_input.text = ""
        self.ids.target_input.text = ""
        self.ids.current_input.text = ""
        self.ids.deadline_input.text = ""
        self.manager.current = "view_savings_goals"
        return


class EditSavingsGoal(Screen):
    goal_index = NumericProperty(-1)

    def on_pre_enter(self, *args):
        if self.goal_index < 0:
            return
        app = App.get_running_app()
        if not (0 <= self.goal_index < len(app.savings_goals)):
            return
        g = app.savings_goals[self.goal_index]
        self.ids.edit_name.text = g.get("name", "")
        self.ids.edit_target.text = str(g.get("target", 0))
        self.ids.edit_current.text = str(g.get("current", 0))
        self.ids.edit_deadline.text = g.get("deadline", "")

    def save_changes(self):
        try:
            app = App.get_running_app()
            if not (0 <= self.goal_index < len(app.savings_goals)):
                return
            g = app.savings_goals[self.goal_index]
            g["name"] = self.ids.edit_name.text
            try:
                g["target"] = float(self.ids.edit_target.text or "0")
            except Exception:
                g["target"] = 0.0
            try:
                g["current"] = float(self.ids.edit_current.text or "0")
            except Exception:
                g["current"] = 0.0
            g["deadline"] = self.ids.edit_deadline.text
            app.save_data()
            try:
                scr = app.root.get_screen("view_savings_goals")
                scr.refresh_list()
            except Exception:
                pass
            self.manager.current = "view_savings_goals"
        except Exception:
            App.get_running_app().show_try_again_popup("Failed to save changes", lambda: self.save_changes())

    def delete_goal(self):
        try:
            app = App.get_running_app()
            if 0 <= self.goal_index < len(app.savings_goals):
                app.savings_goals.pop(self.goal_index)
                app.save_data()
            try:
                scr = app.root.get_screen("view_savings_goals")
                scr.refresh_list()
            except Exception:
                pass
            self.manager.current = "view_savings_goals"
        except Exception:
            App.get_running_app().show_try_again_popup("Failed to delete goal", lambda: self.delete_goal())


class BudgetPlanning(Screen):
    remaining = NumericProperty(0)
    spent = NumericProperty(0)
    total_budget = NumericProperty(0)

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        self.ids.month_spinner.values = months
        if hasattr(app, "active_budget"):
            b = app.active_budget
            self.total_budget = b.get("total_budget", 0)
            self.spent = b.get("spent", 0)
            self.remaining = b.get("remaining", 0)
        else:
            self.total_budget = 0
            self.spent = 0
            self.remaining = 0
        self.ids.total_budget_input.text = str(self.total_budget)
        self.ids.spent_input.text = str(self.spent)
        self.ids.remaining_input.text = app.format_money(self.remaining)

    def save_budget(self):
        app = App.get_running_app()
        raw_total = (self.ids.total_budget_input.text or "").strip()
        raw_spent = (self.ids.spent_input.text or "").strip()
        try:
            total = float(raw_total) if raw_total else 0.0
        except ValueError:
            total = 0.0
        try:
            spent = float(raw_spent) if raw_spent else 0.0
        except ValueError:
            spent = 0.0
        remaining = total - spent
        self.total_budget = total
        self.spent = spent
        self.remaining = remaining
        self.ids.remaining_input.text = app.format_money(remaining)
        month = self.ids.month_spinner.text if hasattr(self.ids, 'month_spinner') else time.strftime('%B')
        if month == "Select Month":
            month = time.strftime('%B')
        app.active_budget = {
            "month": month,
            "total_budget": total,
            "spent": spent,
            "remaining": remaining,
        }
        app.save_data()


class CompletedGoalsScreen(Screen):
    def on_pre_enter(self, *args):
        app = App.get_running_app()
        grid = self.ids.completed_goals_list
        grid.clear_widgets()
        for g in app.savings_goals:
            if not g.get("completed", False):
                continue
            name = g.get("name", "")
            target = g.get("target", 0)
            current = g.get("current", 0)
            deadline = g.get("deadline", "")
            lbl = Label(
                text=f"{name} - {app.format_money(current)} / {app.format_money(target)}  |  {deadline}",
                size_hint_y=None,
                height=40,
            )
            grid.add_widget(lbl)


class BillReminders(Screen):
    def on_pre_enter(self, *args):
        app = App.get_running_app()
        grid = self.ids.bills_list
        grid.clear_widgets()
        for i, b in enumerate(app.bills):
            try:
                item = Factory.BillItem()
                item.index = i
                item.name = str(b.get('name', ''))
                item.amount = float(b.get('amount', 0) or 0)
                item.due = str(b.get('due', ''))
                item.paid = bool(b.get('paid', False))
                grid.add_widget(item)
            except Exception:
                continue

    def add_bill(self):
        app = App.get_running_app()
        name = (self.ids.bill_name_input.text or '').strip()
        if not name:
            if hasattr(self.ids, 'error_label'):
                self.ids.error_label.text = 'Enter bill name'
            return
        try:
            amount = float(self.ids.bill_amount_input.text or '0')
        except Exception:
            amount = 0.0
        due = (self.ids.bill_due_input.text or '').strip()
        new_bill = {'name': name, 'amount': amount, 'due': due, 'paid': False}
        app.bills.append(new_bill)
        try:
            app.save_data()
        except Exception:
            app.show_try_again_popup('Failed to save bill', lambda: self.add_bill())
            return
        self.ids.bill_name_input.text = ''
        self.ids.bill_amount_input.text = ''
        self.ids.bill_due_input.text = ''
        self.on_pre_enter()

    def delete_bill(self, index):
        app = App.get_running_app()
        try:
            idx = int(index)
        except Exception:
            return
        if 0 <= idx < len(app.bills):
            try:
                app.bills.pop(idx)
                app.save_data()
            except Exception:
                app.show_try_again_popup('Failed to delete bill', lambda: self.delete_bill(index))
                return
        self.on_pre_enter()

    def mark_paid(self, index):
        app = App.get_running_app()
        try:
            idx = int(index)
        except Exception:
            return
        if 0 <= idx < len(app.bills):
            try:
                app.bills[idx]['paid'] = True
                app.save_data()
            except Exception:
                app.show_try_again_popup('Failed to mark paid', lambda: self.mark_paid(index))
                return
        self.on_pre_enter()


class SavingsGoalItem(BoxLayout):
    goal_index = NumericProperty(0)
    name = StringProperty("")
    target = StringProperty("")
    current = StringProperty("")
    deadline = StringProperty("")
    has_content = BooleanProperty(False)
    progress = NumericProperty(0)

    def revert(self):
        app = App.get_running_app()
        if not hasattr(app, "savings_goals"):
            return
        try:
            idx = int(self.goal_index)
        except Exception:
            return
        if not (0 <= idx < len(app.savings_goals)):
            return
        g = app.savings_goals[idx]
        self.name = str(g.get("name", ""))
        self.target = str(g.get("target", ""))
        self.current = str(g.get("current", ""))
        self.deadline = g.get("deadline", "")
        self._update_has_content()

    def _update_has_content(self):
        try:
            name = str(self.name or '').strip()
            try:
                t = float(self.target) if str(self.target).strip() != '' else 0.0
            except Exception:
                t = 0.0
            try:
                c = float(self.current) if str(self.current).strip() != '' else 0.0
            except Exception:
                c = 0.0
            dl = str(self.deadline or '').strip()
            self.has_content = bool(name or t > 0 or c > 0 or dl)
        except Exception:
            self.has_content = False

    def on_name(self, instance, value):
        self._update_has_content()

    def on_target(self, instance, value):
        self._update_has_content()

    def on_current(self, instance, value):
        self._update_has_content()

    def on_deadline(self, instance, value):
        self._update_has_content()


class TransactionItem(Label):
    pass


class WindowManager(ScreenManager):
    pass


class UserInfo(Screen):
    pass

class ForgotPinScreen(Screen):
    def send_reset(self):
        email = self.ids.email_input.text.strip()
        if not email:
            self.ids.status_label.text = "Please enter an email."
            self.ids.status_label.color = (1, 0.3, 0.3, 1)
            return

        self.ids.status_label.text = "Reset PIN email sent!"
        self.ids.status_label.color = (0, 1, 0, 1)


class Categories(Screen):
    def on_pre_enter(self, *args):
        app = App.get_running_app()
        try:
            grid = self.ids.categories_list
            grid.clear_widgets()
            for i, name in enumerate(app.categories):
                item = Factory.CategoryItem()
                item.index = i
                item.text = name
                grid.add_widget(item)
        except Exception:
            pass


class BudgetApp(App):
    kv_file = "budget.kv"
    transactions = ListProperty([])
    savings_goals = ListProperty([])
    bills = ListProperty([])
    font_size = NumericProperty(20)
    theme = StringProperty("light")
    primary_color = ListProperty([0, 0, 1, 1])
    button_text_color = ListProperty([1, 1, 1, 1])
    input_bg_color = ListProperty([0.9, 0.9, 1, 1])
    input_text_color = ListProperty([1, 1, 1, 1])
    text_color = ListProperty([1, 1, 1, 1])
    screen_bg_color = ListProperty([1, 1, 1, 1])
    user_name = StringProperty("")
    user_email = StringProperty("")
    pin_hash = StringProperty("")
    pin_salt = StringProperty("")
    pin_iters = NumericProperty(200000)
    currency = StringProperty("$")
    bill_reminders = BooleanProperty(False)
    notifications_enabled = BooleanProperty(False)
    categories = ListProperty([])
    previous_screen = StringProperty("")

    def build(self):
        from kivy.lang import Builder
        self.load_data()
        try:
            self.apply_theme()
        except Exception:
            pass
        Builder.load_file(self.kv_file)
        root = WindowManager()
        root.add_widget(LoginScreen(name="login"))
        root.add_widget(SetupAccount(name="setup_account"))
        root.add_widget(Dashboard(name="dashboard"))
        root.add_widget(AddTransaction(name="add_transaction"))
        root.add_widget(ViewTransactions(name="view_transactions"))
        root.add_widget(BillReminders(name="bill_reminders"))
        root.add_widget(ViewSavingsGoals(name="view_savings_goals"))
        root.add_widget(AddSavingsGoal(name="add_savings_goal"))
        root.add_widget(EditSavingsGoal(name="edit_savings_goal"))
        root.add_widget(BudgetPlanning(name="budget_planning"))
        root.add_widget(Categories(name="categories"))
        root.add_widget(UserInfo(name="user_info"))
        root.add_widget(Settings(name="settings"))
        root.add_widget(CompletedGoalsScreen(name="completed_goals"))
        root.add_widget(ForgotPinScreen(name="forgot_pin"))


        def _on_root_current(instance, value):
            prev = getattr(instance, "last_current", None)
            self.previous_screen = prev or ""
            instance.last_current = value

        root.bind(current=_on_root_current)
        if self.pin_hash:
            root.current = "login"
        else:
            root.current = "setup_account"
        return root

    def go_back(self):
        try:
            if self.previous_screen:
                self.root.current = self.previous_screen
                return
        except Exception:
            pass
        try:
            self.root.current = "dashboard"
        except Exception:
            pass

    def go_home(self):
        try:
            self.root.current = "dashboard"
        except Exception:
            pass

    def open_edit_goal(self, index):
        try:
            idx = int(index)
        except Exception:
            return
        try:
            scr = self.root.get_screen("edit_savings_goal")
        except Exception:
            return
        scr.goal_index = idx
        try:
            scr.on_pre_enter()
        except Exception:
            pass
        self.root.current = "edit_savings_goal"

    def get_bg_color(self):
        try:
            return tuple(self.screen_bg_color)
        except Exception:
            return 1, 1, 1, 1

    def get_text_color(self):
        try:
            return tuple(self.text_color)
        except Exception:
            return 1, 1, 1, 1

    def load_data(self):
        os.makedirs("data", exist_ok=True)
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                self.transactions = json.load(f)
        else:
            self.transactions = []
            self.save_data()
        if os.path.exists(SAVINGS_FILE):
            with open(SAVINGS_FILE, "r") as f:
                self.savings_goals = json.load(f)

            try:
                cleaned = []
                seen = set()
                for g in self.savings_goals:
                    name = str(g.get('name', '')).strip()
                    try:
                        target = float(g.get('target', 0) or 0)
                    except Exception:
                        target = 0.0
                    try:
                        current = float(g.get('current', 0) or 0)
                    except Exception:
                        current = 0.0
                    deadline = str(g.get('deadline', '')).strip()
                    if not name and target == 0 and current == 0 and not deadline:
                        continue
                    key = (name, target, current, deadline)
                    if key in seen:
                        continue
                    seen.add(key)
                    cleaned.append({
                        'name': name,
                        'target': target,
                        'current': current,
                        'deadline': deadline,
                        'completed': bool(g.get('completed', False))
                    })
                self.savings_goals = cleaned
            except Exception:
                pass
            try:
                cleaned = []
                seen = set()
                for g in self.savings_goals:
                    name = str(g.get("name", "")).strip()
                    try:
                        target = float(g.get("target", 0) or 0)
                    except Exception:
                        target = 0.0
                    try:
                        current = float(g.get("current", 0) or 0)
                    except Exception:
                        current = 0.0
                    deadline = str(g.get("deadline", "")).strip()

                    if not name and target == 0 and current == 0 and not deadline:
                        continue

                    key = (name, target, current, deadline)
                    if key in seen:
                        continue
                    seen.add(key)
                    cleaned.append({
                        "name": name,
                        "target": target,
                        "current": current,
                        "deadline": deadline,
                        "completed": bool(g.get("completed", False)),
                    })
                self.savings_goals = cleaned
            except Exception:
                pass
        else:
            self.savings_goals = []
            with open(SAVINGS_FILE, "w") as f:
                json.dump(self.savings_goals, f)
        if os.path.exists(BILLS_FILE):
            try:
                with open(BILLS_FILE, "r") as f:
                    self.bills = json.load(f)
            except Exception:
                self.bills = []
        else:
            self.bills = []
            with open(BILLS_FILE, "w") as f:
                json.dump(self.bills, f)
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                s = json.load(f)
            self.font_size = s.get("font_size", 20)
            self.theme = s.get("theme", "dark").lower()
            self.currency = s.get("currency", "$")
            self.user_name = s.get("user_name", "")
            self.user_email = s.get("user_email", "")
            self.pin_hash = s.get("pin_hash", "")
            self.pin_salt = s.get("pin_salt", "")
            self.pin_iters = s.get("pin_iters", 200000)
            self.bill_reminders = bool(s.get("bill_reminders", False))
            self.notifications_enabled = bool(s.get("notifications_enabled", False))
            self.categories = s.get("categories", [])
            old_pin = s.get("user_pin")
            if old_pin and not self.pin_hash:
                try:
                    salt_hex, hash_hex = self._hash_pin(old_pin)
                    self.pin_salt = salt_hex
                    self.pin_hash = hash_hex
                    self.save_settings()
                except Exception:
                    pass
        else:
            self.theme = "dark"
            self.currency = "$"
            self.font_size = 20
            self.categories = []
            self.save_settings()
        try:
            self.apply_theme()
        except Exception:
            pass

    def format_money(self, amount):
        try:
            symbol = self.currency
            return f"{symbol}{float(amount):,.2f}"
        except Exception:
            return str(amount)

    def save_data(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(self.transactions, f)
        except Exception:
            self.show_try_again_popup("Failed to save transactions to disk", lambda: self.save_data())
            return
        try:
            seen = set()
            deduped = []
            for g in self.savings_goals:
                name = str(g.get("name", "")).strip()
                try:
                    target = float(g.get("target", 0) or 0)
                except Exception:
                    target = 0.0
                try:
                    current = float(g.get("current", 0) or 0)
                except Exception:
                    current = 0.0
                deadline = str(g.get("deadline", "")).strip()
                if not name and target == 0 and current == 0 and not deadline:
                    continue
                key = (name, target, current, deadline)
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(g)
            self.savings_goals = deduped
        except Exception:
            pass
        try:
            seen = set()
            deduped = []
            for g in self.savings_goals:
                name = str(g.get('name', '')).strip()
                try:
                    target = float(g.get('target', 0) or 0)
                except Exception:
                    target = 0.0
                try:
                    current = float(g.get('current', 0) or 0)
                except Exception:
                    current = 0.0
                deadline = str(g.get('deadline', '')).strip()
                if not name and target == 0 and current == 0 and not deadline:
                    continue
                key = (name, target, current, deadline)
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(g)
            self.savings_goals = deduped
        except Exception:
            pass
        try:
            with open(SAVINGS_FILE, "w") as f:
                json.dump(self.savings_goals, f)
        except Exception:
            self.show_try_again_popup("Failed to save savings to disk", lambda: self.save_data())
            return
        try:
            with open(BILLS_FILE, "w") as f:
                json.dump(self.bills, f)
        except Exception:
            self.show_try_again_popup("Failed to save bills to disk", lambda: self.save_data())
            return

    def delete_goal(self, index):
        try:
            idx = int(index)
        except Exception:
            return
        if 0 <= idx < len(self.savings_goals):
            try:
                self.savings_goals.pop(idx)
                self.save_data()
            except Exception:
                self.show_try_again_popup("Failed to delete goal", lambda: self.delete_goal(index))
                return
            try:
                scr = self.root.get_screen("view_savings_goals")
                scr.refresh_list()
            except Exception:
                pass
            try:
                dash = self.root.get_screen("dashboard")
                dash.on_pre_enter()
            except Exception:
                pass

    def complete_goal(self, index):
        try:
            idx = int(index)
        except Exception:
            return
        if 0 <= idx < len(self.savings_goals):
            try:
                self.savings_goals[idx]["completed"] = True
                self.save_data()
            except Exception:
                self.show_try_again_popup("Failed to mark goal completed", lambda: self.complete_goal(index))
                return
            try:
                scr = self.root.get_screen("view_savings_goals")
                scr.refresh_list()
            except Exception:
                pass
            try:
                dash = self.root.get_screen("dashboard")
                dash.on_pre_enter()
            except Exception:
                pass

    def create_new_budget(self):
        self.active_budget = {"total_budget": 0.0, "spent": 0.0, "remaining": 0.0}
        self.save_data()

    def set_current_budget(self, amount=None):
        try:
            if amount is not None:
                amt = float(amount)
                self.active_budget = {"total_budget": amt, "spent": 0.0, "remaining": amt}
                self.save_data()
        except Exception:
            pass

    def manage_categories(self):
        try:
            if hasattr(self, "root") and self.root:
                self.root.current = "categories"
        except Exception:
            pass

    def remove_budget(self):
        if hasattr(self, "active_budget"):
            del self.active_budget
            self.save_data()

    def sign_out(self):
        try:
            if hasattr(self, "root") and self.root:
                self.root.current = "login"
        except Exception:
            pass

    def show_set_budget_prompt(self):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        ti = TextInput(hint_text="Enter budget amount", input_filter="float")
        btns = BoxLayout(size_hint_y=None, height=40, spacing=10)
        ok = Button(text="OK")
        cancel = Button(text="Cancel")

        def on_ok(instance):
            val = ti.text.strip()
            try:
                self.set_current_budget(float(val))
            except Exception:
                pass
            popup.dismiss()

        def on_cancel(instance):
            popup.dismiss()

        ok.bind(on_release=on_ok)
        cancel.bind(on_release=on_cancel)
        btns.add_widget(ok)
        btns.add_widget(cancel)
        content.add_widget(ti)
        content.add_widget(btns)
        popup = Popup(title="Set Current Budget", content=content, size_hint=(0.8, None), height=220)
        popup.open()

    def show_try_again_popup(self, message, retry_callback=None, title="Error"):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        msg = Label(text=message)
        btns = BoxLayout(size_hint_y=None, height=44, spacing=10)
        try_btn = Button(text="Try Again")
        cancel_btn = Button(text="Cancel")

        def on_try(instance):
            popup.dismiss()
            if callable(retry_callback):
                try:
                    retry_callback()
                except Exception:
                    self.show_try_again_popup("Retry failed. Try again?", retry_callback, title)

        try_btn.bind(on_release=on_try)
        cancel_btn.bind(on_release=lambda inst: popup.dismiss())
        btns.add_widget(try_btn)
        btns.add_widget(cancel_btn)
        content.add_widget(msg)
        content.add_widget(btns)
        popup = Popup(title=title, content=content, size_hint=(0.8, None), height=200)
        popup.open()

    def add_category(self, name):
        name = (name or "").strip()
        if not name:
            return
        if name in self.categories:
            return
        self.categories.append(name)
        try:
            self.save_settings()
        except Exception:
            pass
        try:
            if hasattr(self, "root") and self.root:
                scr = self.root.get_screen("categories")
                scr.on_pre_enter()
        except Exception:
            pass

    def remove_category(self, index):
        try:
            idx = int(index)
        except Exception:
            return
        if 0 <= idx < len(self.categories):
            self.categories.pop(idx)
            try:
                self.save_settings()
            except Exception:
                pass
            try:
                if hasattr(self, "root") and self.root:
                    scr = self.root.get_screen("categories")
                    scr.on_pre_enter()
            except Exception:
                pass

    def show_reset_pin_popup(self):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        pin1 = TextInput(hint_text="New PIN", password=True, input_filter="int")
        pin2 = TextInput(hint_text="Confirm PIN", password=True, input_filter="int")
        message = Label(text="")
        btns = BoxLayout(size_hint_y=None, height=40, spacing=10)
        ok = Button(text="OK")
        cancel = Button(text="Cancel")

        def backup_settings():
            try:
                if os.path.exists(SETTINGS_FILE):
                    ts = time.strftime("%Y%m%d-%H%M%S")
                    bak = f"{SETTINGS_FILE}.bak.{ts}"
                    with open(SETTINGS_FILE, "rb") as s, open(bak, "wb") as d:
                        d.write(s.read())
                    return bak
            except Exception:
                pass
            return None

        def on_ok(instance):
            v1 = pin1.text.strip()
            v2 = pin2.text.strip()
            if not v1 or not v2:
                message.text = "Enter PIN in both fields"
                return
            if not v1.isdigit() or not v2.isdigit():
                message.text = "PIN must be numeric"
                return
            if len(v1) < 4:
                message.text = "PIN must be at least 4 digits"
                return
            if v1 != v2:
                message.text = "PINs do not match"
                return
            bak = backup_settings()
            if bak:
                print("[backup] settings backed up to", bak)
            try:
                salt_hex, hash_hex = self._hash_pin(v1)
                self.pin_salt = salt_hex
                self.pin_hash = hash_hex
                self.save_settings()
                message.text = "PIN updated"
            except Exception:
                message.text = "Failed to update PIN"
            popup.dismiss()

        ok.bind(on_release=on_ok)
        cancel.bind(on_release=lambda inst: popup.dismiss())
        btns.add_widget(ok)
        btns.add_widget(cancel)
        content.add_widget(pin1)
        content.add_widget(pin2)
        content.add_widget(message)
        content.add_widget(btns)
        popup = Popup(title="Reset PIN", content=content, size_hint=(0.8, None), height=260)
        popup.open()

    def save_settings(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(
                {
                    "font_size": self.font_size,
                    "theme": self.theme,
                    "user_name": self.user_name,
                    "user_email": self.user_email,
                    "pin_hash": self.pin_hash,
                    "pin_salt": self.pin_salt,
                    "pin_iters": self.pin_iters,
                    "bill_reminders": bool(self.bill_reminders),
                    "notifications_enabled": bool(self.notifications_enabled),
                    "categories": list(self.categories),
                    "currency": self.currency,
                },
                f,
            )

    def _hash_pin(self, pin):
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, int(self.pin_iters))
        return binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode()

    def _verify_pin(self, pin, salt_hex, hash_hex):
        try:
            salt = binascii.unhexlify(salt_hex)
            expected = binascii.unhexlify(hash_hex)
            dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, int(self.pin_iters))
            return hmac.compare_digest(dk, expected)
        except Exception:
            return False

    def apply_theme(self):
        if self.theme and self.theme.lower() == "dark":
            self.primary_color = [0.0, 0.2, 0.5, 1]
            self.text_color = [1, 1, 1, 1]
            self.button_text_color = [1, 1, 1, 1]
            self.input_bg_color = [0.05, 0.1, 0.2, 1]
            self.input_text_color = [1, 1, 1, 1]
            self.screen_bg_color = [0.02, 0.06, 0.12, 1]
        else:
            self.primary_color = [0, 0, 1, 1]
            self.text_color = [1, 1, 1, 1]
            self.button_text_color = [1, 1, 1, 1]
            self.input_bg_color = [0.9, 0.9, 1, 1]
            self.input_text_color = [1, 1, 1, 1]
            self.screen_bg_color = [1, 1, 1, 1]

    def set_theme(self, theme_name):
        self.theme = theme_name.lower()
        self.apply_theme()
        self.save_settings()


if __name__ == "__main__":
    BudgetApp().run()
