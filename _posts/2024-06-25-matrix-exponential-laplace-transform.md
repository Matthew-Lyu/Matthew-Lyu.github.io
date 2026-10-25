---
title: 如何证明矩阵指数e^At的Laplace变换是(sI-A)的逆？
math_title: '如何证明矩阵指数 \(e^{At}\) 的 Laplace 变换是 \((sI-A)\) 的逆？'
date: 2024-06-25 12:00:00 +0800
lang: zh-CN
math: true
description: 在现代控制领域，矩阵指数是一个非常重要的概念，它在描述线性系统的动态行为时起着关键作用。那么，如何证明矩阵指数的 Laplace 变换是 (sI-A) 的逆？
cover: /assets/blog/matrix-exponential-laplace/cover.svg
cover_alt: 矩阵指数等于 (sI-A) 的逆的 Laplace 逆变换
source_url: https://zhuanlan.zhihu.com/p/705003080
---

在现代控制领域, 矩阵指数 $$e^{At}$$ 是一个非常重要的概念, 它在描述线性系统的动态行为时起着关键作用。目前已知一个非常常见的公式是

$$
e^{A t}=\mathcal{L}^{-1}\left[(s I-A)^{-1}\right] \tag{1}
$$

即，矩阵指数矩阵指数 $$e^{At}$$ 的 Laplace 变换是 $$(s I-A)^{-1}$$, 那么如何证明该公式呢？

## 一种常见于参考书上的证明过程：

线性系统的微分方程描述如下：

$$
x^{\prime}(t)=A x(t) + B u(t)\tag{2}
$$

在零输入情况下，系统的微分方程可以简化为:

$$
x^{\prime}(t)=A x(t)\tag{3}
$$

其中 $$x(t)$$ 是状态向量, $$A$$ 是系统矩阵。

根据一阶线性齐次微分方程的通解，我们可以容易得到系统的时域解为：

$$
x(t)=e^{A t} x(0) \tag{4}
$$

换个思路，在复频域中, 通过 Laplace 变换, 我们可以将微分方程转化为复频域方程:

$$
s X(s)-x(0)=A X(s)\tag{5}
$$

解这个方程得到:

$$
X(s)=(s I-A)^{-1} x(0)\tag{6}
$$

为了找到时域解，我们需要对复频域解进行 Laplace 逆变换，即：

$$
x(t)=\mathcal{L}^{-1}\left[(s I-A)^{-1}\right]x(0)\tag{7}
$$

将公式(7)和公式(4)对照，就引出了我们要证明的公式：

$$
e^{A t}=\mathcal{L}^{-1}\left[(s I-A)^{-1}\right]\tag{8}
$$

## 第二种证明方法

第一种方法非常合理，但无法直观地感受到矩阵指数矩阵指数 $$e^{A t}$$ 的 Laplace 变换是 $$(s I-A)^{-1}$$。因此，笔者提出下面这一种证明的策略：

首先, 定义矩阵指数 $$e^{At}$$ 为幂级数形式:

$$
e^{A t}=\sum_{n=0}^{\infty} \frac{(A t)^n}{n!}\tag{9}
$$

我们对上述幂级数进行 Laplace 变换，得到

$$
\mathcal{L}[e^{A t}]=\mathcal{L}\left[\sum_{n=0}^{\infty} \frac{(A t)^n}{n!}\right]\tag{10}
$$

由于 Laplace 变换是线性的，可以逐项变换：

$$
\mathcal{L}[e^{A t}]=\sum_{n=0}^{\infty} \mathcal{L}\left[\frac{(A t)^n}{n!}\right]\tag{11}
$$

进而，考虑矩阵 $$(A t)^n$$ 的 Laplace 变换。利用单项式 $$t^n$$ 的 Laplace 变换公式

$$
\mathcal{L}\left[t^n\right]=\frac{n!}{s^{n+1}}
$$

因此对于矩阵 $$A$$ 有:

$$
\mathcal{L}\left[(A t)^n\right]=A^n \mathcal{L}\left[t^n\right]=A^n \frac{n!}{s^{n+1}}\tag{12}
$$

所以:

$$
\mathcal{L}\left[\frac{(A t)^n}{n!}\right]=A^n \frac{1}{s^{n+1}}\tag{13}
$$

将上述结果代入求和公式:

$$
\mathcal{L}\left[e^{A t}\right]=\sum_{n=0}^{\infty} A^n \frac{1}{s^{n+1}}\tag{14}
$$

这个级数是一个几何级数, 经过求和得到:

$$
\begin{aligned}
\sum_{n=0}^{\infty} A^n \frac{1}{s^{n+1}}
&=\frac{1}{s} \sum_{n=0}^{\infty}\left(\frac{A}{s}\right)^n \\
&=\frac{1}{s}\left(I-\frac{A}{s}\right)^{-1} \\
&=(s I-A)^{-1}
\end{aligned}\tag{15}
$$

因此:

$$
\mathcal{L}\left[e^{A t}\right]=(s I-A)^{-1}\tag{16}
$$

最后，通过Laplace逆变换，我们得到：

$$
e^{A t}=\mathcal{L}^{-1}\left[(s I-A)^{-1}\right]\tag{17}
$$

## 参考文献

[1] 现代控制理论(第2版) 张嗣瀛, 高立群 编著
