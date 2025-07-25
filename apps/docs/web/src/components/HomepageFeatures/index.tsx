import type { ReactElement, ReactNode } from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';
import React from 'react';
import pandasLogo from '@site/static/img/pandas.png'
import pyTorchLogo from '@site/static/img/pyTorch.png'

type FeatureItem = {
	title: string;
	logo: string;
	description: ReactNode;
};

const features: FeatureItem[] = [
	{
		title: 'Pandas',
		logo: pandasLogo,
		description: (
			<p>
				A Python package that provides fast, flexible, and expressive data structures designed to make working with "relational" or "labeled" data both easy and intuitive.
			</p>
		),
	},
	{
		title: 'Pandas',
		logo: pandasLogo,
		description: (
			<p>
				A Python package that provides fast, flexible, and expressive data structures designed to make working with "relational" or "labeled" data both easy and intuitive.
			</p>
		),
	},
	{
		title: 'Matplotlib',
		logo: pandasLogo,
		description: (
			<>
				Matplotlib is the core plotting library in Python, enabling you to generate static, animated, and interactive visualizations with ease.
			</>
		),
	},
	{
		title: 'NumPy',
		logo: pandasLogo,
		description: (
			<>
				NumPy is the foundation of scientific computing in Python. Its fast array operations power everything from machine learning to finance.
			</>
		),
	},
	{
		title: 'PyTorch',
		logo: pyTorchLogo,
		description: (
			<p>
				PyTorch is a flexible deep learning framework that helps researchers and developers build, train, and deploy powerful AI models with ease.
			</p>
		),
	},
	{
		title: 'Powered by React',
		logo: pandasLogo,
		description: (
			<>
				Extend or customize your website layout by reusing React. Docusaurus can
				be extended while reusing the same header and footer.
			</>
		),
	},
];

const Features: React.FC = (): ReactNode => {
	return (
		<section className={styles.features}>
			<div className="container">
				<div className="row">
					{features.map((feature, idx) => (
						<div className={clsx('col col--3 feature')}>
							<div className="text--center">
								<img src={feature.logo} />
							</div>
							<div className="text--center padding-horiz--md">
								{/* <Heading as="h3">{feature.title}</Heading> */}
								<p>{feature.description}</p>
							</div>
						</div>
					))}
				</div>
			</div>
		</section>
	);
}


export default Features