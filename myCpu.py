import os
import matlab.engine
from sklearn.metrics import accuracy_score
from sklearn import metrics
from sklearn.preprocessing import LabelEncoder
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from munkres import Munkres


class LDPKMeans:
    """
    基于ldp-kmeans的离群检测算法
    部分代码参考于Chiyuan Huang为论文《基于局部密度的峰的kmeans算法》编写的程序
    """

    def __init__(self, k2):
        """

        :param k2: 簇中心个数
        """
        # 最大迭代次数
        self.generations = 20
        self.fitk = k2
        # 存放真实值
        self.true = None

    def set_center(self):
        """
        设置簇中心
        :return:
        """
        m = len(self.df_cores)
        index = np.random.randint(0, m)
        cluster_centers = [index]
        d = np.zeros(m)
        for i in range(1, self.k):
            sum_all = 0
            for j in range(m):
                d[j] = min(self.SPD[j, cluster_centers])
                sum_all += d[j]
            sum_all *= 0.6
            d_idx = np.argsort(d)
            d = np.sort(d)
            for j in range(m):
                sum_all -= d[j]
                if sum_all > 0:
                    continue
                cluster_centers.append(d_idx[j])
                break
        self.centers = cluster_centers
        self.centers = np.array([i * (m // self.k) for i in range(self.k)])

    def classify(self):
        """
        划分数据集
        :return:
        """
        for idx in self.index:
            self.reslut[idx] = min([(self.data.iloc[idx, c], c) for c in self.centers])[1]

        for j in range(self.k):
            cent = self.centers[j]
            indexs = self.data.iloc[self.reslut[self.reslut == cent].index,
                                    self.reslut[self.reslut == cent].index].sum().sort_values().index
            self.centers[j] = indexs[0]

    def return_Attribution(self):
        for i in range(len(self.reslut)):
            core = self.reslut[i]
            self.Attribution.loc[self.Attribution['core'] == self.cores[i], 'Class'] = core

    def predict(self):
        """
        开始分析
        :return:
        """
        self.fit()
        self.set_center()

        # 迭代划分数据集
        deep = 0
        while deep < self.generations:
            deep += 1
            old = self.reslut.copy()
            self.classify()
            if (old == self.reslut).all():
                break

        self.return_Attribution()
        idx = 0
        dict = {}
        for i in self.Attribution.Class.unique():
            dict[i] = idx
            idx += 1

        rlt_count = self.Attribution.Class.value_counts()
        rlt_center_index = [int(i) for i in list(rlt_count.keys())]
        rlt_center = {}
        for i in rlt_center_index:
            rlt_center[i] = int(str(rlt_count[i]))

        self.Attribution.Class = self.Attribution.Class.map(dict)
        self.ldppred = self.Attribution.Class.values
        rlt = {
            'acc': '',
            'nmi': '',
            'list': None,
            'dCenters': rlt_center,
        }
        # acc,nmi
        if self.true is not None:
            self.ldppred = self.best_map(self.true, self.ldppred)
            rlt['acc'] = str(accuracy_score(self.true, self.ldppred))
            rlt['nmi'] = str(metrics.normalized_mutual_info_score(self.true, self.ldppred))
        rlt['list'] = self.ldppred
        return rlt

    def read_txt(self, fpath, centers, trueLabel):
        """
        读取数据
        :param fpath: 数据预处理后的数据位置
        :param centers: 簇中心个数
        :param trueLabel: 聚类标记，用于验证算法的结果
        :return:
        """
        self.k = centers
        self.true = trueLabel

        # Start MATLAB process
        engine = matlab.engine.start_matlab()
        self.dat1 = engine.importdata(fpath)
        out = engine.LDP_Searching(self.dat1, nargout=8)

        data = np.array(self.dat1).astype('float')

        df_data = pd.DataFrame(data=data, index=[i for i in range(1, len(data) + 1)])
        self.rho = np.array(out[3]).astype('float')
        knnIndex = np.array(out[0]).astype('int')
        local_core = np.array(out[4]).astype('int').reshape(1, -1)[0]
        self.rho = self.rho.reshape(1, -1)[0]
        Attribution = pd.DataFrame(data=data, index=[i for i in range(1, len(self.rho) + 1)])
        Attribution['core'] = local_core
        o = []
        for _ in set(local_core):
            o.append(data[_ - 1])
        df_cores = pd.DataFrame(data=o)
        self.df_knn = pd.DataFrame(data=knnIndex, index=[i for i in range(1, len(self.rho) + 1)])
        self.Attribution = Attribution
        self.cores = np.array(sorted(set(local_core)))
        self.df_cores = df_cores
        self.df_data = df_data

    def fit(self):
        NLDP = {}
        alls = pd.concat([self.Attribution, self.df_knn], axis=1)
        for cor in self.cores:
            NN = alls.loc[alls.loc[:, 'core'] == cor, :]
            NN_idx = NN.index.tolist()
            NN_knn = NN.values[:, self.df_data.shape[1]:self.df_data.shape[1] + self.fitk].flatten().tolist()
            all = list(map(int, set(NN_knn + NN_idx)))
            NLDP[cor] = all

        maxd = 0
        cores_zb = self.Attribution.iloc[self.cores - 1, :self.df_data.shape[1]]
        SLDP = np.zeros((len(self.cores), len(self.cores)))
        SLDP_data = [[[] for _ in range(len(self.cores))] for __ in range(len(self.cores))]
        for i in range(len(self.cores)):
            for j in range(i):
                a = set(NLDP[self.cores[i]])
                b = set(NLDP[self.cores[j]])
                SLDP[i, j] = len(a & b)
                SLDP[j, i] = len(a & b)
                SLDP_data[i][j] = list(a & b)
                SLDP_data[j][i] = list(a & b)
                A = cores_zb.iloc[i]
                B = cores_zb.iloc[j]
                maxd = max(maxd, np.linalg.norm(A - B))

        maxd *= 100

        SD = np.zeros((len(self.cores), len(self.cores)))
        for i in range(len(self.cores)):
            for j in range(i):
                A = cores_zb.iloc[i]
                B = cores_zb.iloc[j]
                d = np.linalg.norm(A - B)

                if SLDP[i, j] != 0:
                    p = sum(self.rho[np.array(SLDP_data[i][j]) - 1])
                    SD[i, j] = d / (SLDP[i, j] * p)
                else:
                    SD[i, j] = maxd * (1 + d)
                SD[j, i] = SD[i, j]

        SPD = SD.copy()
        for k in range(len(self.cores)):
            for i in range(len(self.cores)):
                for j in range(len(self.cores)):
                    SPD[i, j] = min(SPD[i, j], SPD[i, k] + SPD[k, j])
        self.SPD = SPD
        self.data = pd.DataFrame(SPD)
        self.Attribution['Class'] = np.zeros(len(self.Attribution))
        self.index = [i for i in range(len(self.SPD))]
        self.reslut = pd.Series(data=np.zeros(len(self.SPD)))

    def best_map(self, L1, L2):
        # L1 should be the labels and L2 should be the clustering number we got
        Label1 = np.unique(L1)  # 去除重复的元素，由小大大排列
        nClass1 = len(Label1)  # 标签的大小
        Label2 = np.unique(L2)
        nClass2 = len(Label2)
        nClass = np.maximum(nClass1, nClass2)
        G = np.zeros((nClass, nClass))
        for i in range(nClass1):
            ind_cla1 = L1 == Label1[i]
            ind_cla1 = ind_cla1.astype(float)
            for j in range(nClass2):
                ind_cla2 = L2 == Label2[j]
                ind_cla2 = ind_cla2.astype(float)
                G[i, j] = np.sum(ind_cla2 * ind_cla1)
        m = Munkres()
        index = m.compute(-G.T)
        index = np.array(index)
        c = index[:, 1]
        newL2 = np.zeros(L2.shape)
        for i in range(nClass2):
            newL2[L2 == Label2[i]] = Label1[c[i]]
        return newL2


def previousHandle(arg, pdForm: pd.DataFrame, cacheFile, rltPath=None, imgPath=None):
    """
    数据预处理
    :param arg: 数据预处理的配置，详细内容见下面的对该函数的调用
    :param pdForm: 要处理的数据
    :param cacheFile: 缓存文件路径，保存数据预处理后的数据
    :param rltPath: 聚类标记存放位置
    :param imgPath: 图片存放位置，只有二维数据才有效
    :return:
    """

    columns_len = len(pdForm.columns)

    # 跳过首行
    if arg["skipHeader"]:
        pdForm.drop(index=[0], inplace=True)

    # 缺失值处理
    for i1, i in enumerate(arg['colType']):
        # 丢弃该列
        if arg['handleLoss'][i1] == "删除该列":
            pdForm.drop(columns=[i1], inplace=True)
            continue

        # 数值类型数据的缺失值处理
        if i:
            # 检测传入的参数中”默认填充“的数据能否转为数值类型，不能则更改为0.0
            try:
                arg['defaultFill'][i1] = float(arg['defaultFill'][i1])
            except ValueError:
                arg['defaultFill'][i1] = 0.0

            # 直接类型转换，忽略缺失值
            pdForm.iloc[:, i1] = pdForm.iloc[:, i1].astype('float64', errors='ignore')
            if arg['handleLoss'][i1] == "默认填充":
                pdForm.iloc[:, i1].fillna(arg['defaultFill'][i1], inplace=True)

            elif arg['handleLoss'][i1] == "平均数":
                pdForm.iloc[:, i1].fillna(pdForm.iloc[:, i1].mean(), inplace=True)
            elif arg['handleLoss'][i1] == "中位数":
                pdForm.iloc[:, i1].fillna(pdForm.iloc[:, i1].median(), inplace=True)
            elif arg['handleLoss'][i1] == "众数":
                pdForm.iloc[:, i1].fillna(pdForm.iloc[:, i1].mode()[0], inplace=True)
        # 非数值类型数据的缺失值处理
        else:
            pdForm.iloc[:, i1] = pdForm.iloc[:, i1].astype('str', errors='ignore')
            # 非数值类型数据缺失值的默认填充
            pdForm.iloc[:, i1].fillna(arg['defaultFill'][i1], inplace=True)

            # labelEncoder 编码转为数值类型数据
            encoder = LabelEncoder().fit(pdForm.iloc[:, i1])
            pdForm.iloc[:, i1] = encoder.transform(pdForm.iloc[:, i1])

    # 全部转为数值类型
    pdForm.astype('float64', errors='ignore')
    # 缺失值处理方式：删除数据
    pdForm.dropna(inplace=True)

    # 数据量太少返回错误
    if len(pdForm.index) * 2 < arg['dCenters']:
        return {'status': 1, "info": "能够处理的数据量太少"}

    # 判断是否存在验证列
    if 0 < arg['checkCol'] <= columns_len:
        pass
    elif 0 <= columns_len + arg['checkCol'] + 1 + columns_len < columns_len:
        arg['checkCol'] += columns_len + 1
    elif not (0 < arg['checkCol'] <= columns_len):
        arg['checkCol'] = None
    elif not (0 <= columns_len + arg['checkCol'] + columns_len < columns_len):
        arg['checkCol'] = None

    check_col = None
    if arg['checkCol'] is not None:
        try:
            check_col = pdForm[arg['checkCol']]
        except KeyError:
            arg['checkCol'] = None

    # 确保缓存文件不被占有用
    if os.path.exists(cacheFile):
        os.remove(cacheFile)

    # 有验证列
    if check_col is not None:
        check_col = check_col.values
        arg['dCenters'] = len(set(list(check_col)))

    # 保存数据预处理后的数据
    pdForm.to_csv(cacheFile, sep='\t', index=None, header=None)

    # 基于ldp-kmeans的离群检测算法
    model = LDPKMeans(arg['dCenters'])
    try:
        model.read_txt(cacheFile, arg['dCenters'], check_col)
    # 与matlab有关的错误，数据量为10万以上时触发过这种错误
    except matlab.engine.MatlabExecutionError:
        return {}
    rlt = model.predict()

    # 保存聚类结果
    pd.DataFrame({'a': rlt['list']}).to_csv(rltPath, index=None, header=None)
    del rlt['list']

    # 二维数据绘图
    if columns_len - int(check_col is not None) == 2 and imgPath:
        plt.scatter(model.Attribution[0], model.Attribution[1], s=1, c=model.ldppred)
        plt.savefig(imgPath, dpi=200)
    return rlt


if __name__ == '__main__':
    # 测试
    previousHandle({
        # 跳过首行
        "skipHeader": False,
        # 每列的数据类型（True为数值类型）
        "colType": [True, False],
        # 每列的缺失值处理方式
        "handleLoss": ['默认填充', '默认填充'],
        # 缺失值处理方式为默认填充时，默认要填充的值
        "defaultFill": ['0', '0'],
        # 簇中心个数
        "dCenters": 4,
        # 带簇标记的列，用于做acc和nmi验证, 0表示不进行验证
        "checkCol": 0
    },
        pd.read_csv(
            r'test_dataset\test.csv',
            header=None, sep='\t'),
        r'cache\test.cache.csv',
        r'cache\test.cache.rlt.csv',
    )

