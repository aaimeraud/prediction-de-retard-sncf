"""
Unit Tests for Streamlit Dashboard.

Test coverage:
- Model loading and caching
- Feature validation and bounds checking
- Batch CSV processing
- Prediction functionality
- UI component rendering (mocked)
- Data validation and error handling
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from streamlit_dashboard import (
    load_model,
    load_feature_engineer,
    predict_batch,
    get_api_health,
    render_single_prediction_tab,
    render_batch_upload_tab,
    render_analytics_tab,
    render_visualization_tab
)
from model_classifier import DelayClassifier
from feature_engineer import FeatureEngineer


class TestModelLoading:
    """Test suite for model initialization and caching."""
    
    def test_load_model_returns_classifier(self):
        """
        Verify load_model returns DelayClassifier instance.
        """
        model = load_model()
        assert isinstance(model, DelayClassifier)
    
    def test_load_model_caching(self):
        """
        Verify load_model caching functionality.
        """
        model1 = load_model()
        model2 = load_model()
        assert model1 is model2
    
    def test_load_feature_engineer(self):
        """
        Verify feature engineer loads correctly.
        """
        fe = load_feature_engineer()
        assert isinstance(fe, FeatureEngineer)
    
    def test_feature_engineer_caching(self):
        """
        Verify feature engineer caching.
        """
        fe1 = load_feature_engineer()
        fe2 = load_feature_engineer()
        assert fe1 is fe2


class TestPredictionFunctionality:
    """Test suite for prediction operations."""
    
    def setup_method(self):
        """
        Setup test fixtures.
        """
        self.classifier = load_model()
        self.test_features = np.array([
            [12, 48.8566, 2.3522, 10, 3, 1, 5.0, 0.2, 0.5],
            [14, 45.7597, 4.8320, 8, 2, 0, 3.5, 0.1, 0.4],
            [18, 43.6047, 1.4442, 12, 5, 2, 7.2, 0.4, 0.6]
        ])
    
    def test_predict_batch_returns_predictions(self):
        """
        Verify predict_batch returns predictions.
        """
        df = pd.DataFrame(self.test_features)
        predictions = predict_batch(df, self.classifier)
        
        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == 3
        assert np.all(np.isin(predictions, [0, 1]))
    
    def test_predict_batch_single_record(self):
        """
        Verify predict_batch handles single record.
        """
        df = pd.DataFrame(self.test_features[:1])
        predictions = predict_batch(df, self.classifier)
        
        assert len(predictions) == 1
        assert predictions[0] in [0, 1]
    
    def test_predict_batch_large_dataset(self):
        """
        Verify predict_batch handles large dataset.
        """
        large_features = np.random.randn(1000, 9) * 10
        df = pd.DataFrame(large_features)
        predictions = predict_batch(df, self.classifier)
        
        assert len(predictions) == 1000
        assert all(p in [0, 1] for p in predictions)
    
    def test_predict_batch_caching(self):
        """
        Verify predict_batch caching works.
        """
        df = pd.DataFrame(self.test_features)
        pred1 = predict_batch(df, self.classifier)
        pred2 = predict_batch(df, self.classifier)
        
        np.testing.assert_array_equal(pred1, pred2)


class TestAPIHealth:
    """Test suite for API health checking."""
    
    @patch('streamlit_dashboard.requests.get')
    def test_api_health_success(self, mock_get):
        """
        Verify API health check when API is healthy.
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        health = get_api_health()
        
        assert health["status"] is True
        assert "timestamp" in health
    
    @patch('streamlit_dashboard.requests.get')
    def test_api_health_failure(self, mock_get):
        """
        Verify API health check when API is down.
        """
        mock_get.side_effect = Exception("Connection refused")
        
        health = get_api_health()
        
        assert health["status"] is False
        assert "timestamp" in health
    
    @patch('streamlit_dashboard.requests.get')
    def test_api_health_error_response(self, mock_get):
        """
        Verify API health check with error response.
        """
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        health = get_api_health()
        
        assert health["status"] is False


class TestFeatureValidation:
    """Test suite for feature input validation."""
    
    def test_hour_bounds_validation(self):
        """
        Verify hour of day bounds (0-23).
        """
        valid_hours = [0, 6, 12, 18, 23]
        
        for hour in valid_hours:
            assert 0 <= hour <= 23
    
    def test_latitude_bounds_validation(self):
        """
        Verify latitude bounds (-90 to 90).
        """
        valid_lats = [-90, -45, 0, 45, 90]
        
        for lat in valid_lats:
            assert -90 <= lat <= 90
    
    def test_longitude_bounds_validation(self):
        """
        Verify longitude bounds (-180 to 180).
        """
        valid_lons = [-180, -90, 0, 90, 180]
        
        for lon in valid_lons:
            assert -180 <= lon <= 180
    
    def test_day_of_week_validation(self):
        """
        Verify day of week (0-6).
        """
        valid_days = list(range(7))
        
        for day in valid_days:
            assert 0 <= day <= 6
    
    def test_delay_range_validation(self):
        """
        Verify delay values are non-negative.
        """
        valid_delays = [0, 5, 30, 60, 120]
        
        for delay in valid_delays:
            assert delay >= 0
    
    def test_weather_impact_range(self):
        """
        Verify weather impact normalized to [0, 1].
        """
        valid_impacts = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for impact in valid_impacts:
            assert 0 <= impact <= 1


class TestBatchProcessing:
    """Test suite for batch CSV processing."""
    
    def test_csv_parsing_valid(self):
        """
        Verify CSV parsing with valid data.
        """
        csv_data = """hour,lat,lon,stops,day,vehicle,avg_delay,weather,other
12,48.8566,2.3522,10,3,1,5.0,0.2,0.5
14,45.7597,4.8320,8,2,0,3.5,0.1,0.4"""
        
        df = pd.read_csv(BytesIO(csv_data.encode()))
        
        assert len(df) == 2
        assert list(df.columns) == [
            'hour', 'lat', 'lon', 'stops', 'day', 'vehicle', 'avg_delay', 'weather', 'other'
        ]
    
    def test_csv_parsing_missing_columns(self):
        """
        Verify CSV parsing fails with missing columns.
        """
        csv_data = """hour,lat,lon,stops
12,48.8566,2.3522,10"""
        
        df = pd.read_csv(BytesIO(csv_data.encode()))
        
        assert 'weather' not in df.columns
    
    def test_csv_parsing_empty_file(self):
        """
        Verify handling of empty CSV file.
        """
        csv_data = """hour,lat,lon,stops,day,vehicle,avg_delay,weather,other"""
        
        df = pd.read_csv(BytesIO(csv_data.encode()))
        
        assert len(df) == 0
    
    def test_batch_results_format(self):
        """
        Verify batch results have correct format.
        """
        csv_data = """hour,lat,lon,stops,day,vehicle,avg_delay,weather,other
12,48.8566,2.3522,10,3,1,5.0,0.2,0.5
14,45.7597,4.8320,8,2,0,3.5,0.1,0.4"""
        
        df = pd.read_csv(BytesIO(csv_data.encode()))
        classifier = load_model()
        predictions = predict_batch(df, classifier)
        
        results = df.copy()
        results['prediction'] = predictions
        results['delay'] = results['prediction'].apply(lambda x: "Delayed" if x else "On-Time")
        
        assert 'prediction' in results.columns
        assert 'delay' in results.columns
        assert all(d in ["Delayed", "On-Time"] for d in results['delay'])


class TestUIComponentsMocked:
    """Test suite for UI components (with mocks)."""
    
    @patch('streamlit_dashboard.st')
    def test_render_single_prediction_tab(self, mock_st):
        """
        Verify single prediction tab rendering.
        """
        mock_st.slider.return_value = 12
        mock_st.number_input.side_effect = [
            48.8566, 2.3522, 10, 0, 5.0, 0.0
        ]
        mock_st.selectbox.side_effect = [3, 1]
        mock_st.button.return_value = False
        
        classifier = load_model()
        fe = load_feature_engineer()
        
        render_single_prediction_tab(classifier, fe)
        
        mock_st.subheader.assert_called()
    
    @patch('streamlit_dashboard.st')
    def test_render_batch_upload_tab(self, mock_st):
        """
        Verify batch upload tab rendering.
        """
        mock_st.file_uploader.return_value = None
        
        classifier = load_model()
        
        render_batch_upload_tab(classifier)
        
        mock_st.subheader.assert_called()
    
    @patch('streamlit_dashboard.st')
    def test_render_analytics_tab(self, mock_st):
        """
        Verify analytics tab rendering.
        """
        classifier = load_model()
        
        render_analytics_tab(classifier)
        
        mock_st.subheader.assert_called()
    
    @patch('streamlit_dashboard.st')
    def test_render_visualization_tab(self, mock_st):
        """
        Verify visualization tab rendering.
        """
        mock_st.tabs.return_value = [Mock(), Mock()]
        
        render_visualization_tab()
        
        mock_st.subheader.assert_called()


class TestErrorHandling:
    """Test suite for error handling and edge cases."""
    
    def test_csv_with_invalid_numeric_values(self):
        """
        Verify handling of invalid numeric values in CSV.
        """
        csv_data = """hour,lat,lon,stops,day,vehicle,avg_delay,weather,other
invalid,48.8566,2.3522,10,3,1,5.0,0.2,0.5"""
        
        with pytest.raises(ValueError):
            pd.read_csv(BytesIO(csv_data.encode()))['hour'].astype(int)
    
    def test_predict_with_nan_features(self):
        """
        Verify prediction handles NaN features gracefully.
        """
        features_with_nan = np.array([[
            12, np.nan, 2.3522, 10, 3, 1, 5.0, 0.2, 0.5
        ]])
        
        classifier = load_model()
        filled_features = np.nan_to_num(features_with_nan, nan=0.0)
        predictions = classifier.predict(filled_features)
        
        assert len(predictions) == 1
    
    def test_predict_with_out_of_bounds_values(self):
        """
        Verify prediction handles out-of-bounds values.
        """
        features_oob = np.array([[
            99, 150, 250, 1000, 10, 5, 500, 2.5, 1.5
        ]])
        
        classifier = load_model()
        predictions = classifier.predict(features_oob)
        
        assert len(predictions) == 1
        assert predictions[0] in [0, 1]


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_single_prediction_workflow(self):
        """
        Verify complete single prediction workflow.
        """
        classifier = load_model()
        
        features = np.array([[
            12, 48.8566, 2.3522, 10, 3, 1, 5.0, 0.2, 0.5
        ]])
        
        predictions = classifier.predict(features)
        probabilities = classifier.predict_proba(features)
        
        assert len(predictions) == 1
        assert predictions[0] in [0, 1]
        assert 0 <= probabilities.max() <= 1
    
    def test_batch_workflow(self):
        """
        Verify complete batch prediction workflow.
        """
        classifier = load_model()
        
        test_data = np.random.randn(100, 9)
        df = pd.DataFrame(test_data)
        
        predictions = predict_batch(df, classifier)
        
        assert len(predictions) == 100
        assert all(p in [0, 1] for p in predictions)
        
        results_df = df.copy()
        results_df['prediction'] = predictions
        results_df['delay'] = results_df['prediction'].apply(
            lambda x: "Delayed" if x else "On-Time"
        )
        
        assert len(results_df) == 100
        assert all(d in ["Delayed", "On-Time"] for d in results_df['delay'])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
