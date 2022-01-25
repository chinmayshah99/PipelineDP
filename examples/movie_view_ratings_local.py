""" Demo of running PipelineDP locally, without any external data processing framework"""

from absl import app
from absl import flags
import pipeline_dp

from examples.example_utils import parse_file, write_to_file

FLAGS = flags.FLAGS
flags.DEFINE_string('input_file', None, 'The file with the movie view data')
flags.DEFINE_string('output_file', None, 'Output file')


def main(unused_argv):
    # Here, we use a local backend for computations. Which does not depend on
    # any pipeline framework and it is implemented in pure Python in
    # PipelineDP. It keeps all data in memory and is not optimized for large data.
    # For datasets smaller than ~tens of megabytes, local execution without any
    # framework is faster than local mode with Beam or Spark.
    backend = pipeline_dp.LocalBackend()

    # Define the privacy budget available for our computation.
    budget_accountant = pipeline_dp.NaiveBudgetAccountant(total_epsilon=1,
                                                          total_delta=1e-6)

    # Load and parse input data
    movie_views = parse_file(FLAGS.input_file)

    # Create a DPEngine instance.
    dp_engine = pipeline_dp.DPEngine(budget_accountant, backend)

    params = pipeline_dp.AggregateParams(
        noise_kind=pipeline_dp.NoiseKind.LAPLACE,
        metrics=[
            # we can compute multiple metrics at once.
            pipeline_dp.Metrics.COUNT,
            pipeline_dp.Metrics.SUM,
            pipeline_dp.Metrics.PRIVACY_ID_COUNT
        ],
        # Limit contributions of each user.
        max_partitions_contributed=2,
        max_contributions_per_partition=1,
        min_value=1,
        max_value=5)

    # Specify how to extract privacy_id, partition_key and value from an
    # element of movie_views.
    data_extractors = pipeline_dp.DataExtractors(
        partition_extractor=lambda mv: mv.movie_id,
        privacy_id_extractor=lambda mv: mv.user_id,
        value_extractor=lambda mv: mv.rating)

    # Create a computational graph for the aggregation.
    # All computations are lazy. dp_result is iterable, but iterating it would
    # fail until budget computed (below).
    # It’s possible to call DPEngine.aggregate multiple times with different
    # metrics to compute.
    dp_result = dp_engine.aggregate(movie_views, params, data_extractors)

    # Make budget computations.
    budget_accountant.compute_budgets()

    # Here's where the lazy iterator initiates computations and gets transformed
    # into actual results
    dp_result = list(dp_result)

    # Save the results
    write_to_file(dp_result, FLAGS.output_file)

    return 0


if __name__ == '__main__':
    flags.mark_flag_as_required("input_file")
    flags.mark_flag_as_required("output_file")
    app.run(main)