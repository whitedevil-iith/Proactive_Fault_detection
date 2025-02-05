import pandas as pd

# Read the CSV file into a pandas DataFrame
df = pd.read_csv('prometheus_combined.csv')

# Check for columns with at least one non-zero, NaN, or non-empty value
filtered_columns = df.columns[
    (df != 0).any() |      # Has at least one non-zero value
    (df.isna()).any() |    # Has at least one NaN value
    (df.astype(bool)).any() # Has at least one non-empty value
]

# Further remove columns that contain only constant values (where all values are the same)
filtered_columns = filtered_columns[df[filtered_columns].nunique() > 1]

# Filter the DataFrame with the selected columns
filtered_df = df[filtered_columns]

# Save the filtered DataFrame to a new CSV file
filtered_df.to_csv('filtered_file.csv', index=False)

# Save the column names to a text file
with open('usefulQuery.txt', 'w') as file:
    for column in filtered_columns:
        # if("fs" not in column):
        file.write(f"{column}\n")
