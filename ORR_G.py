#!/work/home/jinshuyang/anaconda3/envs/py39_env/bin/python
import pandas as pd
import sys
import os
import subprocess

# data_folder can be passed to the script using sys.argv[1]: O OH OOH
data_folder = sys.argv[1]
print(f"Data folder: {data_folder}")

data1 = pd.read_csv(f"{data_folder}/Edft.txt", sep='\t', header=None, names=['Species', 'Edft'])
data2 = pd.read_csv(f"{data_folder}/2-thermal/Gcorr.txt", sep='\t', header=None, names=['Species', 'Gcorr'])

merged_data = pd.merge(data1, data2, on='Species')
merged_data.to_csv('merged_file.csv', index=False)

df = pd.read_csv('merged_file.csv')
sums = df.iloc[:, 1:3].sum(axis=1)
df['G'] = sums
df.to_csv('processed_data.csv', index=False)


data3 = pd.read_csv('Support/Edft.txt', sep='\t', header=None, names=['Species', 'Edft'])
data4 = pd.read_csv("processed_data.csv", sep=',', header=None, names=['Species', 'Edft', 'Gcorr', 'G'])

merged_data = pd.merge(data3, data4, on='Species')
merged_data.to_csv('merged_file2.csv', index=False)

df2 = pd.read_csv('merged_file2.csv',header=0)
new_df2 = df2.iloc[:, [0, 1, 4]]
new_df2 = new_df2.rename(columns={new_df2.columns[0]: 'Species', 
                                new_df2.columns[1]: 'E_support',
                                new_df2.columns[2]: f"{data_folder}"})

new_df2.to_csv('processed_data2.csv', index=False)

df3 = pd.read_csv('processed_data2.csv',header=0)
if data_folder == "OOH":
	deltaG = df3.iloc[:, 2] - df3.iloc[:, 1] - 2*(-14.219603) + 1.5*(-6.80186909)
elif data_folder == "O":
	deltaG = df3.iloc[:, 2] - df3.iloc[:, 1] - (-14.219603) + 1*(-6.80186909)
elif data_folder == "OH":
	deltaG = df3.iloc[:, 2] - df3.iloc[:, 1] - (-14.219603) + 0.5*(-6.80186909)
elif data_folder == "H2O2":
        deltaG = df3.iloc[:, 2] - df3.iloc[:, 1] - 2*(-14.219603) + 1*(-6.80186909)
else:
	print("The variable does not match any of the conditions.")
df3['deltaG'] = deltaG
new_df3 = df3.iloc[:, [0, 3]]
new_df3 = new_df3.rename(columns={new_df3.columns[0]: 'Species',
	new_df3.columns[1]: 'delta_G'})
new_df3.to_csv(f"{data_folder}.csv", index=False)

# remove the temporary files
files_to_delete = ["merged_file.csv", "merged_file2.csv", "processed_data.csv", "processed_data2.csv"]
for file in files_to_delete:
    os.remove(file)

