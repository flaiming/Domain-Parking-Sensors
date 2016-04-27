#!/usr/bin/env python

import csv
from pybrain.tools.shortcuts import buildNetwork
from pybrain.supervised import BackpropTrainer

from pybrain.datasets import SupervisedDataSet

CSV_PARKED = 'parked_samples_features.csv'
CSV_BENIGN = 'benign_samples_features.csv'

DATA = (
    (CSV_PARKED, 1),
    (CSV_BENIGN, 0)
)


class WebsiteFeaturesDataSet(SupervisedDataSet):

    def __init__(self):
        SupervisedDataSet.__init__(self, 3, 1)

        for file_name, expected in DATA:
            with open(file_name, 'rb') as csvfile:
                csvreader = csv.reader(csvfile, delimiter=',')
                for row in csvreader:
                    row_data = []
                    for d in row:
                        try:
                            row_data.append(float(d))
                        except ValueError:
                            pass
                    if row_data:
                        self.addSample([row_data[i] for i in [0, 6, 9]], [expected])
                        #self.addSample(row_data, [expected])
        print self


def testTraining():
    ds = WebsiteFeaturesDataSet()
    net = buildNetwork(ds.indim, 4, ds.outdim, recurrent=True)
    trainer = BackpropTrainer(net, learningrate=0.001, momentum=0.99, verbose=True)
    trainer.trainOnDataset(ds, 1000)
    trainer.testOnData(verbose=True)
    import pdb; pdb.set_trace()


if __name__ == '__main__':
    testTraining()
