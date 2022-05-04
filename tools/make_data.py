from sklearn.datasets import make_blobs
import pandas
import sys


PATH = r'test_dataset/'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('缺少数据集名称')
        exit()
    x, y = make_blobs(n_samples=10000,
                      n_features=3,
                      centers=3,
                      cluster_std=1.0,
                      center_box=(0, 10),
                      random_state=None)

    data = pandas.DataFrame(x)
    data[len(data.columns)] = pandas.Series(y)

    data.to_csv(PATH + sys.argv[1]+'.csv', header=False, index=False)
