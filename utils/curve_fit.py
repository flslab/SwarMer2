import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def power_law(x, a, b):
    return a * np.exp(b * np.log(x))


if __name__ == '__main__':
    # Read the CSV file
    data = pd.read_csv(
        '/Users/hamed/Downloads/outdegree2.csv')  # Make sure to replace 'data.csv' with your actual file name

    # Extract x and y values
    x = data['OutDegree'].values
    y = data['Cnt'].values

    # Perform the curve fitting
    params, covariance = np.polyfit(np.log(x), np.log(y), deg=1, cov=True)
    a, b = np.exp(params)

    # Generate the fitted curve
    x_fit = np.linspace(min(x), max(x), 100)
    y_fit = power_law(x_fit, a, b)

    # Plot the original data and fitted curve
    plt.scatter(x, y, label='Original Data')
    plt.plot(x_fit, y_fit, label=f'Fitted Curve: y = {a:.2f}x^{b:.2f}', color='red')
    plt.xlabel('x')
    plt.ylabel('y')
    plt.yscale('log')
    plt.legend()
    plt.show()
