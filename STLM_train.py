import sys
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt
#import pickle
import itertools
import statsmodels.api as sm
from sklearn.model_selection import KFold
'''
python3 tetranucl.csv pickleFileLoc(must have .pickle at the end) > TTN_descr.txt

1. Read in the TTN csv
2. Perform 10 fold cross validation to train and test the model
3. Print details about the TTN coefs 
3. Plot predict vs. actual LFC
4. Plot the STLM coef vs. mean LFC per TTN
5. Train the regression model on all the data and save it to the pickle file and then tar it
'''
####################################################################################
# read in file 
sample_name = sys.argv[1].replace('.csv','')
sample_name = sample_name.split('/')[-1]

tetra_nucl_data = pd.read_csv(sys.argv[1])
tetra_nucl_data = tetra_nucl_data[tetra_nucl_data["State"]!="ES"]
tetra_nucl_data.reset_index(inplace=True, drop=True)
tetra_nucl_data = tetra_nucl_data.dropna()

y = tetra_nucl_data["LFC"]
X = tetra_nucl_data.drop(["Coord","ORF ID","ORF Name","Count","Local Mean","LFC","State"],axis=1)

#####################################################################################
#                               Train Regression Model 
#####################################################################################
#perform 10-Fold cross validation and train-test the models
R2_list= []
kf = KFold(n_splits=10)
for train_index, test_index in kf.split(X):
	X_train, X_test = X.loc[train_index], X.loc[test_index]
	y_train, y_test = y.loc[train_index], y.loc[test_index]
	X_train = sm.add_constant(X_train)
	X_test = sm.add_constant(X_test)
	model = sm.OLS(y_train,X_train)
	results = model.fit()
	y_pred = results.predict(X_test)
	R2_list.append(r2_score(y_test, y_pred))

#Fit the model and save it in the pickle file passed into system args
X = sm.add_constant(X)
final_model = sm.OLS(y,X).fit()
results.save(sys.argv[2],remove_data=True)

#tar the file to save space
import tarfile
tar = tarfile.open(sys.argv[2]+".tar.gz", "w:gz")
for name in [sys.argv[2]]:tar.add(name)
tar.close()
#delete orginal copy of pickle file since it is in the tar file
import os
os.remove(sys.argv[2])

#output TTN information
combos=[''.join(p) for p in itertools.product(['A','C','T','G'], repeat=4)]
c_averages = []
combo_coef={}
for idx,c in enumerate(combos):
        c_tetra = tetra_nucl_data[tetra_nucl_data[c]==1]
        c_averages.append(c_tetra["LFC"].mean())
        combo_coef[c]=[results.params[idx+1],len(c_tetra)]
#print the ttn,coef assocaited and count ttn is observed
print("Tetra-nucleotide"+"\t"+"STLM Coefficient"+"\t"+"Number of times observed")
for val in sorted(combo_coef.items(), key=lambda x: x[1], reverse=True):
        print(str(val[0])+"\t"+str(val[1][0])+"\t"+str(val[1][1]))

#####################################################################################################################
#                                      FIGURES
#####################################################################################################################

#Predicted vs. Actual LFC of the final cross-validation train-test split
fig, (ax1) = plt.subplots(1, sharex=True, sharey=True)
fig.suptitle("Testing trained STLM model of: "+str(sample_name))
ax1.set_title("Predicted vs. Actual LFC")
ax1.scatter(y_test,y_pred,s=1,c='green',alpha=0.5)
ax1.set_xlabel('Actual')
ax1.set_ylabel('Predicted')
ax1.text(-7, 7, "R2: "+ str(sum(R2_list) / len(R2_list)), fontsize=10) #R2 is average of the R2 values from the cross-validation train-test split
ax1.axhline(y=0, color='k')
ax1.axvline(x=0, color='k')
ax1.plot([-8,8], [-8,8], 'k--', alpha=0.75, zorder=1)
ax1.set_xlim(-8,8)
ax1.set_ylim(-8,8)
ax1.grid(zorder=0)

#STLM Coef vs. meanLFcs per TTN plot
fig, (ax1) = plt.subplots(1, sharex=True, sharey=True)
fig.suptitle(str(sample_name)+ " TetraNucl MeanCount-STLM Coefficent Correlation")
ax1.scatter(c_averages,results.params[1:],s=5,c='green',alpha=0.75)
ax1.set_xlabel('LFC Average')
ax1.set_ylabel('STLM Coefficents')
ax1.axhline(y=0, color='k')
ax1.axvline(x=0, color='k')
ax1.plot([-3,3], [-3,3], 'k--', alpha=0.25, zorder=1)
ax1.grid(zorder=0)


from statsmodels.stats.multitest import fdrcorrection
Models_pvalues = pd.DataFrame(results.pvalues[1:],columns=["Pvalues"])
Models_pvalues["Coef"] = results.params[1:]
Models_pvalues["Adjusted Pvalues"] = fdrcorrection(results.pvalues[1:],alpha=0.05)[1]
insig_models_pval = Models_pvalues[Models_pvalues["Adjusted Pvalues"]>0.05]

#Coef Plot
fig, ax = plt.subplots(figsize=(40,5))
x = np.arange(256)
ax.bar(x,results.params[1:])
ax.plot([0,256], [insig_models_pval["Coef"].min(), insig_models_pval["Coef"].min()], "k--")
ax.plot([0,256], [insig_models_pval["Coef"].max(), insig_models_pval["Coef"].max()], "k--")
ax.set_xticks(range(256))
ax.set_xticklabels(results.params[1:].index, rotation=90)
ax.set_title("Coefficients from STLM Model")
ax.set_xlabel("Tetranucleotides")
ax.set_ylabel("Ceofficient")
ax.grid(True)

plt.show()
