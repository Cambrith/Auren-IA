export default {
	test: {
		include: [
			'src/lib/utils/birthDate.test.ts',
			'src/lib/utils/aurenConnections.test.ts',
			'src/lib/utils/modelBrand.test.ts',
			'src/lib/utils/imageSelection.test.ts',
			'src/lib/utils/aurenTask.test.ts',
			'src/lib/utils/aurenStartup.test.ts'
		],
		pool: 'forks',
		poolOptions: { forks: { singleFork: true } }
	}
};
