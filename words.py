import tkinter as tk
from tkinter import messagebox, ttk
import random
import pyttsx3
import pandas as pd
import os
import Levenshtein

# 初始化 pyttsx3 引擎
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1)

# 读取所有词汇数据（确保vocab1.csv包含category列）
all_data = pd.read_csv('vocab.csv', header=0) if os.path.exists('vocab.csv') else pd.DataFrame()
WRONG_WORDS_FILE = "wrong_words.csv"


class WordQuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智能单词学习助手")
        self.root.geometry("800x600")
        self.root.configure(bg="#f8f9fa")

        # 核心状态变量
        self.score = 0
        self.total_questions = 0  # 用户设定的总题数
        self.current_question_num = 0  # 当前已答题目数
        self.current_wrong_words = []
        self.wrong_words = self.load_wrong_words()
        self.current_question = None
        self.options = []
        self.data = None
        self.mode = 'english_to_chinese'

        # 创建界面组件
        self.create_widgets()

    def create_widgets(self):
        # ---------- 设置区域框架 ----------
        settings_frame = ttk.LabelFrame(self.root, text="学习设置", padding=15)
        settings_frame.pack(pady=10, padx=20, fill=tk.X)

        # 类别选择
        ttk.Label(settings_frame, text="词汇类别:", font=("微软雅黑", 12)).grid(row=0, column=0, padx=5, sticky=tk.W)
        self.category_var = tk.StringVar()
        self.category_combobox = ttk.Combobox(settings_frame, textvariable=self.category_var,
                                              values=["四级", "六级", "雅思"], state="readonly", width=15)
        self.category_combobox.grid(row=0, column=1, padx=5)
        self.category_combobox.set("四级")

        # 模式选择
        ttk.Label(settings_frame, text="学习模式:", font=("微软雅黑", 12)).grid(row=0, column=2, padx=20, sticky=tk.W)
        self.mode_var = tk.StringVar(value=self.mode)
        ttk.Radiobutton(settings_frame, text="英文→中文", variable=self.mode_var, value='english_to_chinese').grid(
            row=0, column=3)
        ttk.Radiobutton(settings_frame, text="中文→英文", variable=self.mode_var, value='chinese_to_english').grid(
            row=0, column=4)

        # 题目数量
        ttk.Label(settings_frame, text="题目数量:", font=("微软雅黑", 12)).grid(row=1, column=0, padx=5, pady=10,
                                                                                sticky=tk.W)
        self.question_num_var = tk.StringVar()
        self.question_num_entry = ttk.Entry(settings_frame, textvariable=self.question_num_var, width=8)
        self.question_num_entry.grid(row=1, column=1, padx=5)
        self.question_num_entry.insert(0, "10")  # 默认10题
        ttk.Label(settings_frame, text="（1-50题）", font=("微软雅黑", 10), foreground="#666").grid(row=1, column=2,
                                                                                                  sticky=tk.W)

        # ---------- 测试区域框架 ----------
        quiz_frame = ttk.LabelFrame(self.root, text="测试区域", padding=15)
        quiz_frame.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)

        # 题目显示
        self.question_label = ttk.Label(quiz_frame, text="点击开始测试", font=("微软雅黑", 16), wraplength=700)
        self.question_label.pack(pady=20)

        # 选项按钮（使用ttk.Style优化样式）
        style = ttk.Style()
        style.configure('TButton', font=("微软雅黑", 12), padding=5)
        self.option_buttons = []
        for i in range(4):
            btn = ttk.Button(quiz_frame, text=f"选项 {i + 1}", width=40, command=lambda i=i: self.check_answer(i))
            btn.pack(pady=8, fill=tk.X, padx=20)
            self.option_buttons.append(btn)
            btn.state(['disabled'])  # 初始禁用

        # ---------- 控制区域 ----------
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(pady=5)

        self.start_button = ttk.Button(control_frame, text="开始测试", width=15, command=self.start_test)
        self.start_button.grid(row=0, column=0, padx=10)

        self.end_button = ttk.Button(control_frame, text="结束测试", width=15, state=tk.DISABLED, command=self.end_test)
        self.end_button.grid(row=0, column=1, padx=10)

        self.review_button = ttk.Button(control_frame, text="查看错题本", width=15, command=self.review_wrong_words)
        self.review_button.grid(row=0, column=2, padx=10)

        # 状态提示
        self.status_label = ttk.Label(self.root, text="状态：未开始测试", font=("微软雅黑", 11), foreground="#666")
        self.status_label.pack(pady=5)

    def load_wrong_words(self):
        """加载历史错题（优化去重逻辑）"""
        if os.path.exists(WRONG_WORDS_FILE):
            df = pd.read_csv(WRONG_WORDS_FILE)
            return df.drop_duplicates(subset=['english', 'category'], keep='last').to_dict('records')
        return []

    def save_wrong_words(self):
        """保存错题（自动去重）"""
        if self.current_wrong_words:
            df = pd.DataFrame(self.current_wrong_words)
            # 合并历史错题并去重
            if os.path.exists(WRONG_WORDS_FILE):
                old_df = pd.read_csv(WRONG_WORDS_FILE)
                df = pd.concat([old_df, df]).drop_duplicates(subset=['english', 'category'], keep='last')
            df.to_csv(WRONG_WORDS_FILE, index=False)

    def start_test(self):
        """启动测试（增加输入验证和状态管理）"""
        # 输入验证
        try:
            self.total_questions = int(self.question_num_var.get())
            if not 1 <= self.total_questions <= 50:
                raise ValueError
        except:
            messagebox.showerror("输入错误", "题目数量必须为1-50之间的整数")
            return

        # 数据验证
        category = self.category_var.get()
        self.data = all_data[all_data['category'] == category]
        if self.data.empty:
            messagebox.showerror("数据错误", f"未找到[{category}]类别的词汇，请检查vocab1.csv文件")
            return

        # 初始化测试状态
        self.score = 0
        self.current_question_num = 0
        self.current_wrong_words = []
        self.mode = self.mode_var.get()

        # 启用/禁用按钮
        for btn in self.option_buttons:
            btn.state(['!disabled'])
        self.start_button.state(['disabled'])
        self.end_button.state(['!disabled'])
        self.category_combobox.state(['disabled'])
        self.question_num_entry.state(['disabled'])

        # 开始第一题
        self.status_label.config(text=f"状态：正在测试（{self.current_question_num}/{self.total_questions}）")
        self.next_question()

    def next_question(self):
        """生成下一题（优化相似性选项逻辑）"""
        self.current_question_num += 1

        # 达到设定题数时结束测试
        if self.current_question_num > self.total_questions:
            self.end_test()
            return

        # 随机选择题目
        self.current_question = self.data.sample(1).iloc[0].to_dict()
        correct_answer = None
        candidates = []

        # 英文→中文模式：生成中文释义相似的选项
        if self.mode == 'english_to_chinese':
            correct_answer = self.current_question['chinese']
            # 规则：找包含相同2字以上的中文释义（或使用近义词库）
            keyword = self._extract_keyword(correct_answer)  # 提取关键字
            # 筛选相似候选（排除正确答案）
            similar_candidates = self.data[
                (self.data['chinese'].str.contains(keyword)) &
                (self.data['chinese'] != correct_answer)
            ]['chinese'].drop_duplicates().tolist()
            # 不足时用随机候选补充
            candidates = similar_candidates + self.data['chinese'].drop_duplicates().tolist()
            # 播放英文发音
            engine.say(self.current_question['english'])
            engine.runAndWait()
            self.question_label.config(
                text=f"【第{self.current_question_num}题】英文单词：{self.current_question['english']}"
            )

        # 中文→英文模式：生成拼写相似的选项
        else:
            correct_answer = self.current_question['english']
            # 规则：计算编辑距离（越小越相似）
            self.data['distance'] = self.data['english'].apply(
                lambda x: Levenshtein.distance(x, correct_answer)
            )
            # 筛选距离1-3的相似单词（排除正确答案）
            similar_candidates = self.data[
                (self.data['distance'].between(1, 3)) &
                (self.data['english'] != correct_answer)
            ]['english'].drop_duplicates().tolist()
            # 不足时用随机候选补充
            candidates = similar_candidates + self.data['english'].drop_duplicates().tolist()
            self.question_label.config(
                text=f"【第{self.current_question_num}题】中文释义：{self.current_question['chinese']}"
            )

        # 生成最终选项（去重并打乱）
        self.options = [correct_answer]
        # 从候选列表中随机选取不重复的干扰项
        while len(self.options) < 4 and candidates:
            candidate = random.choice(candidates)
            if candidate not in self.options:
                self.options.append(candidate)
                candidates.remove(candidate)  # 避免重复选择
        # 如果候选不足（极端情况），用随机填充
        while len(self.options) < 4:
            random_candidate = random.choice(self.data[
                self.data[list(self.data.columns)[0]] != correct_answer
            ][list(self.data.columns)[0]].tolist())
            if random_candidate not in self.options:
                self.options.append(random_candidate)
        random.shuffle(self.options)

        # 更新选项按钮
        for i, btn in enumerate(self.option_buttons):
            btn.config(text=self.options[i])

        # 更新状态提示
        self.status_label.config(text=f"状态：正在测试（{self.current_question_num}/{self.total_questions}）")

    def _extract_keyword(self, chinese_str):
        """辅助函数：提取中文释义的关键字（简单实现）"""
        # 规则：取最后2个字符作为关键字（可根据实际数据调整）
        return chinese_str[-2:] if len(chinese_str) >= 2 else chinese_str

    def check_answer(self, selected_idx):
        """检查答案（优化错题记录逻辑）"""
        correct_answer = self.current_question['chinese'] if self.mode == 'english_to_chinese' else \
        self.current_question['english']
        user_answer = self.options[selected_idx]

        if user_answer == correct_answer:
            self.score += 1
            messagebox.showinfo("回答正确", "恭喜，你答对了！", parent=self.root)
        else:
            # 记录本次测试错题（按单词去重）
            if not any(w['english'] == self.current_question['english'] for w in self.current_wrong_words):
                self.current_wrong_words.append(self.current_question)
            messagebox.showerror("回答错误", f"正确答案是：{correct_answer}", parent=self.root)

        # 自动进入下一题
        self.next_question()

    def end_test(self):
        """结束测试（优化结果展示）"""
        # 禁用相关组件
        for btn in self.option_buttons:
            btn.state(['disabled'])
        self.end_button.state(['disabled'])
        self.start_button.state(['!disabled'])
        self.category_combobox.state(['!disabled'])
        self.question_num_entry.state(['!disabled'])

        # 保存本次错题
        self.save_wrong_words()

        # 计算正确率
        accuracy = (self.score / self.total_questions) * 100 if self.total_questions > 0 else 0

        # 结果弹窗
        result_window = tk.Toplevel(self.root)
        result_window.title("测试结果")
        result_window.geometry("600x400")
        result_window.configure(bg="#f8f9fa")

        ttk.Label(result_window, text="测试结果报告", font=("微软雅黑", 18), padding=10).pack()
        ttk.Label(result_window, text=f"总题数：{self.total_questions}", font=("微软雅黑", 14)).pack(pady=5)
        ttk.Label(result_window, text=f"正确数：{self.score}", font=("微软雅黑", 14)).pack(pady=5)
        ttk.Label(result_window, text=f"正确率：{accuracy:.2f}%", font=("微软雅黑", 14), foreground="#28a745").pack(
            pady=5)

        if self.current_wrong_words:
            ttk.Label(result_window, text="本次错题：", font=("微软雅黑", 14), padding=10).pack(anchor=tk.W)
            text = tk.Text(result_window, height=8, width=60, wrap=tk.WORD)
            text.pack(padx=10)
            for idx, word in enumerate(self.current_wrong_words, 1):
                text.insert(tk.END, f"{idx}. {word['english']} → {word['chinese']}\n")
        else:
            ttk.Label(result_window, text="本次无错题，表现优异！", font=("微软雅黑", 14), foreground="#28a745").pack(
                pady=20)

        ttk.Button(result_window, text="关闭", command=result_window.destroy, width=15).pack(pady=10)

    def review_wrong_words(self):
        """查看错题本（优化筛选和显示）"""
        if not self.wrong_words:
            messagebox.showinfo("错题本", "错题本为空，继续保持！", parent=self.root)
            return

        review_window = tk.Toplevel(self.root)
        review_window.title("错题本")
        review_window.geometry("700x500")
        review_window.configure(bg="#f8f9fa")

        # 筛选组件
        filter_frame = ttk.Frame(review_window, padding=10)
        filter_frame.pack(fill=tk.X)

        ttk.Label(filter_frame, text="筛选类别:", font=("微软雅黑", 12)).grid(row=0, column=0, padx=5)
        category_var = tk.StringVar()
        category_combobox = ttk.Combobox(filter_frame, textvariable=category_var,
                                         values=["全部", "四级", "六级", "雅思"], state="readonly", width=10)
        category_combobox.grid(row=0, column=1, padx=5)
        category_combobox.set("全部")

        # 错题列表
        tree = ttk.Treeview(review_window, columns=('类别', '单词', '释义'), show='headings', height=18)
        tree.heading('类别', text='类别')
        tree.heading('单词', text='单词')
        tree.heading('释义', text='正确释义')
        tree.column('类别', width=100)
        tree.column('单词', width=200)
        tree.column('释义', width=300)
        tree.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        def update_tree():
            tree.delete(*tree.get_children())
            selected_cat = category_var.get()
            for word in self.wrong_words:
                if selected_cat == "全部" or word['category'] == selected_cat:
                    tree.insert('', tk.END, values=(
                        word['category'],
                        word['english'],
                        word['chinese']
                    ))

        category_combobox.bind("<<ComboboxSelected>>", lambda e: update_tree())
        update_tree()  # 初始加载

        ttk.Button(review_window, text="关闭", command=review_window.destroy, width=15).pack(pady=5)


if __name__ == "__main__":
    root = tk.Tk()
    app = WordQuizApp(root)
    root.mainloop()