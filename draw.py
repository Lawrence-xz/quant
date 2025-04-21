import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置matplotlib使用中文支持的字体
rcParams['font.family'] = 'SimHei'
rcParams['axes.unicode_minus'] = False


def draw_net_value(money_changes):
    net_values = [10000]  # 初始资金
    for delta in money_changes:
        net_values.append(net_values[-1] + delta)

    plt.figure(figsize=(14, 7))
    plt.plot(net_values[:-1], label='账户净值', color='b')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()  # 自动调整子图参数,使之填充整个图像区域
    plt.show()


def draw_win_lose_dash(all_lists, colors):
    names = ['win', 'lose', 'lack_lose', 'wrong_lose', 'invalid']
    # 绘制散点图
    plt.figure(figsize=(25, 5))  # 设置图表大小

    # 遍历所有组，并绘制散点图
    for i, (group, color) in enumerate(zip(all_lists, colors)):
        plt.scatter(group, [i] * len(group), c=color, label=f'{names[i]}', alpha=0.7, s=1)

    # 添加标题和标签
    plt.title('Visualization of Groups with Custom all_lists and Colors')
    plt.xlabel('Point Value')
    plt.yticks(range(len(all_lists)), [f'Group {i + 1}' for i in range(len(all_lists))])  # 设置 y 轴标签
    plt.legend()  # 显示图例
    plt.grid(axis='x', linestyle='--', alpha=0.7)  # 添加网格线（仅 x 轴）

    # 显示图表
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    pass
