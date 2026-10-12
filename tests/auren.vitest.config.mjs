export default {
	test: {
		include: [
			'src/lib/utils/birthDate.test.ts',
			'src/lib/utils/modelBrand.test.ts',
			'src/lib/utils/imageSelection.test.ts'
		],
		pool: 'forks',
		poolOptions: { forks: { singleFork: true } }
	}
};
